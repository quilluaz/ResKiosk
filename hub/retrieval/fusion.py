import os
from dataclasses import dataclass, field
from typing import Optional, Sequence


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


RRF_K = _env_int("RESKIOSK_RRF_K", 60)
HYBRID_TOP_K = _env_int("RESKIOSK_HYBRID_TOP_K", 5)


@dataclass(frozen=True)
class RankedCandidate:
    article_id: int
    score: float
    rank: int


@dataclass(frozen=True)
class FusedCandidate:
    article_id: int
    fusion_score: float
    rank: int
    vector_rank: Optional[int] = None
    lexical_rank: Optional[int] = None
    vector_score: Optional[float] = None
    lexical_score: Optional[float] = None
    overlap_count: int = 0
    best_rank: int = 0
    tie_break_key: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class FusionOutput:
    strategy: str
    parameters: dict
    results: list[FusedCandidate]
    tie_breaks: list[dict]


def _rank_or_large(rank: Optional[int]) -> int:
    return rank if rank is not None else 1_000_000


def rrf_fuse(
    vector_candidates: Sequence[RankedCandidate],
    lexical_candidates: Sequence[RankedCandidate],
    top_k: int = HYBRID_TOP_K,
    rrf_k: int = RRF_K,
) -> FusionOutput:
    """Fuse vector and lexical rankings using Reciprocal Rank Fusion.

    Sorting is deterministic and independent of input ordering:
    fusion score desc, overlap count desc, best rank asc, vector rank asc,
    lexical rank asc, article ID asc.
    """
    vector_by_id = {c.article_id: c for c in vector_candidates}
    lexical_by_id = {c.article_id: c for c in lexical_candidates}
    article_ids = set(vector_by_id) | set(lexical_by_id)

    scored = []
    for article_id in article_ids:
        vector = vector_by_id.get(article_id)
        lexical = lexical_by_id.get(article_id)
        fusion_score = 0.0
        ranks = []

        if vector:
            fusion_score += 1.0 / (rrf_k + vector.rank)
            ranks.append(vector.rank)
        if lexical:
            fusion_score += 1.0 / (rrf_k + lexical.rank)
            ranks.append(lexical.rank)

        overlap_count = int(vector is not None) + int(lexical is not None)
        best_rank = min(ranks) if ranks else _rank_or_large(None)
        sort_key = (
            -fusion_score,
            -overlap_count,
            best_rank,
            _rank_or_large(vector.rank if vector else None),
            _rank_or_large(lexical.rank if lexical else None),
            article_id,
        )
        scored.append((sort_key, article_id, fusion_score, vector, lexical, overlap_count, best_rank))

    scored.sort(key=lambda item: item[0])

    results = []
    tie_breaks = []
    for output_rank, (sort_key, article_id, fusion_score, vector, lexical, overlap_count, best_rank) in enumerate(
        scored[:top_k],
        start=1,
    ):
        candidate = FusedCandidate(
            article_id=article_id,
            fusion_score=round(fusion_score, 6),
            rank=output_rank,
            vector_rank=vector.rank if vector else None,
            lexical_rank=lexical.rank if lexical else None,
            vector_score=round(float(vector.score), 6) if vector else None,
            lexical_score=round(float(lexical.score), 6) if lexical else None,
            overlap_count=overlap_count,
            best_rank=best_rank,
            tie_break_key=sort_key,
        )
        results.append(candidate)
        tie_breaks.append(
            {
                "article_id": article_id,
                "overlap_count": overlap_count,
                "best_rank": best_rank,
                "vector_rank": candidate.vector_rank,
                "lexical_rank": candidate.lexical_rank,
            }
        )

    return FusionOutput(
        strategy="rrf",
        parameters={"rrf_k": rrf_k, "top_k": top_k},
        results=results,
        tie_breaks=tie_breaks,
    )
