"""
Exact-term retrieval evaluation: vector-only vs hybrid on a fixed KB snapshot.

Designed for Sprint 3 Slice 4 Story 6 (Person 4). Uses:
  - SQLite in-memory DB seeded from JSON (reproducible corpus text for BM25)
  - Patched cosine scores per query (reproducible vector ranking without model drift)
  - Patched corpus loader (same article dicts + matrix shape as snapshot)

Run:
  python -m hub.eval.exact_term_retrieval_eval
  python -m hub.eval.exact_term_retrieval_eval --json-out results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from contextlib import ExitStack
from typing import Any, Optional
from unittest.mock import patch

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hub.db import schema
from hub.db.session import Base
from hub.retrieval import search
from hub.retrieval.fusion import HYBRID_TOP_K, RRF_K
from hub.retrieval.lexical import LexicalSearchOutput, invalidate_lexical_index
from hub.retrieval.search import THRESHOLD, invalidate_corpus_cache

logger = logging.getLogger(__name__)

DEFAULT_DATA = Path(__file__).resolve().parent / "data" / "exact_term_retrieval_eval_v1.json"


class _FakeEmbedder:
    def embed_text(self, _text: str):
        return np.array([1.0, 0.0], dtype=np.float32)


class _FakeCosine:
    def __init__(self, scores: list[float]):
        self._scores = np.array(scores, dtype=np.float64)

    def __getitem__(self, _idx):
        return self

    def numpy(self):
        return self._scores


def _data_path(explicit: Optional[str | Path] = None) -> Path:
    return Path(explicit) if explicit else DEFAULT_DATA


def load_eval_bundle(path: Optional[str | Path] = None) -> dict[str, Any]:
    p = _data_path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _article_row(spec: dict[str, Any]) -> schema.KBArticle:
    return schema.KBArticle(
        id=int(spec["id"]),
        question=spec["question"],
        answer=spec["answer"],
        category=spec.get("category") or "general",
        tags=spec.get("tags") or "",
        enabled=1,
        source="eval_snapshot",
        created_at=0,
        last_updated=0,
        embedding=None,
    )


def build_memory_session(bundle: dict[str, Any]) -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    kb_version = int(bundle.get("kb_version", 1))
    db.add(schema.SystemVersion(id=1, kb_version=kb_version, last_published=0))
    for spec in bundle["articles"]:
        db.add(_article_row(spec))
    db.commit()
    return db


def _corpus_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    order = [int(x) for x in bundle["corpus_article_order"]]
    by_id = {int(a["id"]): a for a in bundle["articles"]}
    articles = []
    for aid in order:
        a = by_id[aid]
        raw_tags = a.get("tags") or ""
        tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
        articles.append(
            {
                "id": int(a["id"]),
                "question": a["question"],
                "answer": a["answer"],
                "category": a.get("category") or "general",
                "tags": tags_list,
            }
        )
    n = len(articles)
    matrix = np.ones((n, 2), dtype=np.float32)
    return {"matrix": matrix, "articles": articles}


def _empty_lexical():
    return LexicalSearchOutput(results=[], latency_ms=0.0)


def _retrieve_with_mode(
    db: Session,
    bundle: dict[str, Any],
    query_spec: dict[str, Any],
    *,
    hybrid: bool,
    corpus: dict[str, Any],
) -> dict[str, Any]:
    scores = [float(x) for x in query_spec["vector_cosine_scores"]]
    if len(scores) != len(corpus["articles"]):
        raise ValueError(
            f"Query {query_spec['id']}: expected {len(corpus['articles'])} vector_cosine_scores, got {len(scores)}"
        )

    def fake_load_corpus(_db, excluded_ids=None):
        return corpus

    patches = [
        patch("hub.retrieval.search._intent_classifier", None),
        patch("hub.retrieval.search.filter_policy.compute_excluded_article_ids", return_value=frozenset()),
        patch("hub.retrieval.search.get_shelter_config", return_value={}),
        patch("hub.retrieval.search.inventory_module.check_inventory", return_value=None),
        patch("hub.retrieval.search.load_embedder", return_value=_FakeEmbedder()),
        patch("hub.retrieval.search._load_corpus", side_effect=fake_load_corpus),
        patch("hub.retrieval.search.util.cos_sim", return_value=_FakeCosine(scores)),
    ]
    if not hybrid:
        patches.append(patch("hub.retrieval.search.lexical_search", return_value=_empty_lexical()))

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        return search.retrieve(
            db,
            query_spec["query"],
            is_retry=False,
            exclude_source_ids=None,
            query_language="en",
        )


def _rank_of_first_hit(ordered_ids: list[int], evidence_ids: list[int]) -> Optional[int]:
    ev = set(int(x) for x in evidence_ids)
    for i, aid in enumerate(ordered_ids):
        if int(aid) in ev:
            return i + 1
    return None


def _top_k_hit(fusion_ids: list[int], evidence_ids: list[int], k: int) -> bool:
    head = [int(x) for x in fusion_ids[:k]]
    ev = set(int(x) for x in evidence_ids)
    return bool(ev.intersection(head))


def _top1_hit_fusion(fusion_ids: list[int], evidence_ids: list[int]) -> bool:
    """Rank-1 retrieval hit (fusion list), independent of answer gating/clarification."""
    if not fusion_ids:
        return False
    return int(fusion_ids[0]) in set(int(x) for x in evidence_ids)


@dataclass
class QueryEvalResult:
    query_id: str
    eval_class: str
    mode: str
    fusion_top_k_ids: list[int]
    vector_top_k_ids: list[int]
    source_id: Optional[int]
    answer_type: str
    top1_hit: bool
    topk_hit: bool
    rank_of_evidence: Optional[int]


def evaluate_query(
    db: Session,
    bundle: dict[str, Any],
    query_spec: dict[str, Any],
    corpus: dict[str, Any],
    *,
    hybrid: bool,
) -> QueryEvalResult:
    mode = "hybrid" if hybrid else "vector_only"
    out = _retrieve_with_mode(db, bundle, query_spec, hybrid=hybrid, corpus=corpus)
    fusion_ids = [int(x) for x in (out.get("fusion_top_k_ids") or [])]
    vector_ids = [int(x) for x in (out.get("vector_top_k_ids") or [])]
    evidence = [int(x) for x in query_spec["evidence_ids"]]
    k = int(query_spec.get("eval_top_k") or HYBRID_TOP_K)
    sid = out.get("source_id")
    sid_i = int(sid) if sid is not None else None

    return QueryEvalResult(
        query_id=str(query_spec["id"]),
        eval_class=str(query_spec.get("eval_class") or "unknown"),
        mode=mode,
        fusion_top_k_ids=fusion_ids,
        vector_top_k_ids=vector_ids,
        source_id=sid_i,
        answer_type=str(out.get("answer_type") or ""),
        top1_hit=_top1_hit_fusion(fusion_ids, evidence),
        topk_hit=_top_k_hit(fusion_ids, evidence, k),
        rank_of_evidence=_rank_of_first_hit(fusion_ids, evidence),
    )


def run_eval(
    bundle: Optional[dict[str, Any]] = None,
    *,
    data_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    bundle = bundle or load_eval_bundle(data_path)
    corpus = _corpus_from_bundle(bundle)

    invalidate_corpus_cache()
    invalidate_lexical_index()

    db = build_memory_session(bundle)
    try:
        per_query = []
        vec_top1 = []
        vec_topk = []
        hy_top1 = []
        hy_topk = []
        stability_rows = []

        for q in bundle["queries"]:
            invalidate_lexical_index()

            r_vec = evaluate_query(db, bundle, q, corpus, hybrid=False)
            invalidate_lexical_index()
            r_hy = evaluate_query(db, bundle, q, corpus, hybrid=True)

            per_query.append(
                {
                    "id": q["id"],
                    "eval_class": q.get("eval_class"),
                    "evidence_ids": q["evidence_ids"],
                    "eval_top_k": int(q.get("eval_top_k") or HYBRID_TOP_K),
                    "vector_only": r_vec.__dict__,
                    "hybrid": r_hy.__dict__,
                }
            )

            vec_top1.append(r_vec.top1_hit)
            vec_topk.append(r_vec.topk_hit)
            hy_top1.append(r_hy.top1_hit)
            hy_topk.append(r_hy.topk_hit)

            if q.get("stability_check"):
                gold = int(q["evidence_ids"][0])
                rv = _rank_of_first_hit(r_vec.fusion_top_k_ids, [gold])
                rh = _rank_of_first_hit(r_hy.fusion_top_k_ids, [gold])
                if rv is not None and rh is not None:
                    ok = rh <= rv
                elif rv is None and rh is not None:
                    ok = True
                else:
                    ok = rh is not None
                stability_rows.append(
                    {
                        "query_id": q["id"],
                        "gold": gold,
                        "vector_rank": rv,
                        "hybrid_rank": rh,
                        "stable_or_improved": ok,
                    }
                )

        n = len(bundle["queries"])
        report = {
            "snapshot_id": bundle.get("snapshot_id"),
            "kb_version": bundle.get("kb_version"),
            "eval_version": bundle.get("eval_version"),
            "config": {
                "hybrid_top_k": HYBRID_TOP_K,
                "rrf_k": RRF_K,
                "threshold": THRESHOLD,
                "reskiosk_sim_threshold": os.environ.get("RESKIOSK_SIM_THRESHOLD"),
                "reskiosk_rrf_k": os.environ.get("RESKIOSK_RRF_K"),
                "reskiosk_hybrid_top_k": os.environ.get("RESKIOSK_HYBRID_TOP_K"),
            },
            "metrics": {
                "vector_only": {
                    "top1_accuracy": sum(vec_top1) / n if n else 0.0,
                    "topk_accuracy": sum(vec_topk) / n if n else 0.0,
                    "n": n,
                },
                "hybrid": {
                    "top1_accuracy": sum(hy_top1) / n if n else 0.0,
                    "topk_accuracy": sum(hy_topk) / n if n else 0.0,
                    "n": n,
                },
                "stability": {
                    "checked_queries": len(stability_rows),
                    "stable_or_improved": sum(1 for r in stability_rows if r["stable_or_improved"]),
                    "details": stability_rows,
                },
            },
            "per_query": per_query,
            "generated_at_ms": int(time.time() * 1000),
        }
        return report
    finally:
        db.close()
        invalidate_corpus_cache()
        invalidate_lexical_index()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run exact-term retrieval eval (vector vs hybrid).")
    parser.add_argument("--data", type=str, default=None, help="Path to eval JSON (default: bundled v1).")
    parser.add_argument("--json-out", type=str, default=None, help="Write full report JSON to this path.")
    args = parser.parse_args()

    report = run_eval(data_path=args.data)
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
