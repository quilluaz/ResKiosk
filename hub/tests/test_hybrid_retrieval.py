import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from hub.db import schema
from hub.retrieval import search
from hub.retrieval.lexical import LexicalResult, LexicalSearchOutput


class _FakeEmbedder:
    def embed_text(self, _text):
        return np.array([1.0])


class _FakeCosine:
    def __init__(self, scores):
        self._scores = np.array(scores)

    def __getitem__(self, _idx):
        return self

    def numpy(self):
        return self._scores


class _FakeQuery:
    def __init__(self, rows=None):
        self._rows = rows or []

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeDb:
    def __init__(self, articles=None):
        self._articles = articles or []

    def query(self, *entities):
        if entities and entities[0] is schema.KBArticle:
            return _FakeQuery(self._articles)
        return _FakeQuery([])


def _article(article_id, question="Question", answer="Answer", category="general"):
    return {
        "id": article_id,
        "question": question,
        "answer": answer,
        "category": category,
        "tags": [],
    }


def _orm_article(article_id, question="Question", answer="Answer", category="general"):
    return SimpleNamespace(
        id=article_id,
        question=question,
        answer=answer,
        category=category,
        tags="",
    )


class TestHybridRetrieval(unittest.TestCase):
    def _run_retrieve(self, *, corpus_articles, vector_scores, lexical_output, db=None, exclude=None):
        matrix = np.ones((len(corpus_articles), 1))
        db = db or _FakeDb()
        with (
            patch("hub.retrieval.search._intent_classifier", None),
            patch("hub.retrieval.search.get_shelter_config", return_value={}),
            patch("hub.retrieval.search.inventory_module.check_inventory", return_value=None),
            patch("hub.retrieval.search.load_embedder", return_value=_FakeEmbedder()),
            patch("hub.retrieval.search._load_corpus", return_value={"matrix": matrix, "articles": corpus_articles}),
            patch("hub.retrieval.search.util.cos_sim", return_value=_FakeCosine(vector_scores)),
            patch("hub.retrieval.search.lexical_search", return_value=lexical_output),
        ):
            return search.retrieve(
                db,
                "medical station",
                is_retry=False,
                exclude_source_ids=exclude,
                query_language="en",
            )

    def test_vector_only_behavior_still_works(self):
        result = self._run_retrieve(
            corpus_articles=[
                _article(1, question="Medical station", answer="Go to room A.", category="medical"),
                _article(2, question="Food line", answer="Go to room B.", category="food"),
            ],
            vector_scores=[0.91, 0.2],
            lexical_output=LexicalSearchOutput(results=[], latency_ms=1.2),
        )

        self.assertEqual(result["answer_type"], "DIRECT_MATCH")
        self.assertEqual(result["source_id"], 1)
        self.assertEqual(result["vector_top_k_ids"], [1, 2])
        self.assertEqual(result["lexical_top_k_ids"], [])
        self.assertEqual(result["fusion_strategy"], "rrf")

    def test_lexical_rank_one_can_win_when_vector_candidate_is_excluded(self):
        result = self._run_retrieve(
            corpus_articles=[_article(1, question="Other", answer="Other answer.")],
            vector_scores=[0.2],
            lexical_output=LexicalSearchOutput(
                results=[LexicalResult(article_id=2, bm25_score=5.0, rank=1)],
                latency_ms=2.5,
            ),
            db=_FakeDb([
                _orm_article(2, question="Medical station", answer="Go to the clinic.", category="medical")
            ]),
            exclude=[1],
        )

        self.assertEqual(result["answer_type"], "DIRECT_MATCH")
        self.assertEqual(result["source_id"], 2)
        self.assertEqual(result["confidence_source"], "lexical_rank1")
        self.assertEqual(result["confidence_raw"], 0.2)
        self.assertNotIn(1, result["fusion_top_k_ids"])

    def test_excluded_ids_do_not_appear_in_vector_or_fused_results(self):
        result = self._run_retrieve(
            corpus_articles=[
                _article(1, question="Hidden", answer="Hidden."),
                _article(2, question="Visible", answer="Visible."),
            ],
            vector_scores=[0.95, 0.85],
            lexical_output=LexicalSearchOutput(results=[], latency_ms=0.5),
            exclude=[1],
        )

        self.assertEqual(result["source_id"], 2)
        self.assertNotIn(1, result["vector_top_k_ids"])
        self.assertNotIn(1, result["fusion_top_k_ids"])


if __name__ == "__main__":
    unittest.main()
