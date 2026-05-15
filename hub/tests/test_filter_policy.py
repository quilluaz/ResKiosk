"""
hub/tests/test_filter_policy.py

Tests for Person 2 — Retrieval Safety + Filter Enforcement.

Covers:
  - Disabled/unpublished article exclusion
  - Quarantined metadata exclusion
  - Rejected metadata exclusion
  - Approved metadata remains usable
  - No validation record → article included (backwards-compatible)
  - Hard rules run before validation/filter
  - Lexical path filtering
  - Vector path filtering
  - Hybrid fused result filtering (post-fusion defense-in-depth)
  - Logging: exclusion reason codes and candidate counts
"""

import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from hub.db.session import Base
from hub.db import schema
from hub.retrieval.filter_policy import (
    compute_excluded_article_ids,
    get_exclusion_log,
    filter_fused_results,
    REASON_DISABLED,
    REASON_QUARANTINED,
    REASON_REJECTED,
    REASON_CALLER_EXCLUDED,
)


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _seed_articles(db: Session, articles: list[dict]) -> list[schema.KBArticle]:
    """Create KB articles from a list of dicts with keys: id, question, answer, enabled."""
    created = []
    for art_data in articles:
        art = schema.KBArticle(
            id=art_data["id"],
            question=art_data.get("question", f"Q{art_data['id']}"),
            answer=art_data.get("answer", f"A{art_data['id']}"),
            category=art_data.get("category", "General"),
            enabled=art_data.get("enabled", 1),
            created_at=int(datetime.utcnow().timestamp()),
            last_updated=int(datetime.utcnow().timestamp()),
        )
        db.add(art)
        created.append(art)
    db.commit()
    return created


def _seed_validation_status(db: Session, items: list[dict]):
    """Create KBItemValidationStatus rows.

    Each dict: {kb_item_id, status, kb_version (optional), publish_attempt_id (optional)}
    """
    for item in items:
        vs = schema.KBItemValidationStatus(
            kb_item_id=item["kb_item_id"],
            status=item["status"],
            kb_version=item.get("kb_version", 1),
            publish_attempt_id=item.get("publish_attempt_id"),
        )
        db.add(vs)
    db.commit()


class TestComputeExcludedArticleIds(unittest.TestCase):
    """Tests for compute_excluded_article_ids()."""

    def setUp(self):
        self.engine = _make_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_no_articles_returns_empty(self):
        """Empty KB → empty exclusion set."""
        db = self.SessionLocal()
        result = compute_excluded_article_ids(db)
        self.assertEqual(result, frozenset())
        db.close()

    def test_disabled_articles_excluded(self):
        """Articles with enabled=0 are excluded."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1},
            {"id": 2, "enabled": 0},
            {"id": 3, "enabled": 1},
            {"id": 4, "enabled": 0},
        ])
        result = compute_excluded_article_ids(db)
        self.assertIn(2, result)
        self.assertIn(4, result)
        self.assertNotIn(1, result)
        self.assertNotIn(3, result)
        db.close()

    def test_quarantined_articles_excluded(self):
        """Articles with latest validation status 'quarantined' are excluded."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1},
            {"id": 2, "enabled": 1},
            {"id": 3, "enabled": 1},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "quarantined"},
            {"kb_item_id": 3, "status": "approved"},
        ])
        result = compute_excluded_article_ids(db)
        self.assertIn(2, result)
        self.assertNotIn(1, result)
        self.assertNotIn(3, result)
        db.close()

    def test_rejected_articles_excluded(self):
        """Articles with latest validation status 'rejected' are excluded."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1},
            {"id": 2, "enabled": 1},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "rejected"},
        ])
        result = compute_excluded_article_ids(db)
        self.assertIn(2, result)
        self.assertNotIn(1, result)
        db.close()

    def test_approved_articles_remain_usable(self):
        """Articles with status 'approved' are NOT excluded."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1},
            {"id": 2, "enabled": 1},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "approved"},
        ])
        result = compute_excluded_article_ids(db)
        self.assertNotIn(1, result)
        self.assertNotIn(2, result)
        db.close()

    def test_no_validation_record_not_excluded(self):
        """Articles with no validation record are included (backwards-compatible)."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1},
            {"id": 2, "enabled": 1},
        ])
        # No validation records at all
        result = compute_excluded_article_ids(db)
        self.assertNotIn(1, result)
        self.assertNotIn(2, result)
        db.close()

    def test_latest_status_wins(self):
        """When multiple validation rows exist, the latest (highest ID) wins."""
        db = self.SessionLocal()
        _seed_articles(db, [{"id": 1, "enabled": 1}])
        # First quarantined, then approved → should be included
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "quarantined", "kb_version": 1},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved", "kb_version": 2},
        ])
        result = compute_excluded_article_ids(db)
        self.assertNotIn(1, result, "Article should be included since latest status is 'approved'")
        db.close()

    def test_latest_status_quarantined_overrides_older_approved(self):
        """If latest validation status is quarantined, article is excluded
        even if there was a previous approved record."""
        db = self.SessionLocal()
        _seed_articles(db, [{"id": 1, "enabled": 1}])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved", "kb_version": 1},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "quarantined", "kb_version": 2},
        ])
        result = compute_excluded_article_ids(db)
        self.assertIn(1, result, "Article should be excluded since latest status is 'quarantined'")
        db.close()

    def test_needs_review_not_excluded(self):
        """Articles with status 'needs_review' are NOT excluded from retrieval.

        needs_review means human review is pending but the article is still
        safe to surface (per Person 2 spec: only quarantined and rejected block).
        """
        db = self.SessionLocal()
        _seed_articles(db, [{"id": 1, "enabled": 1}])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "needs_review"},
        ])
        result = compute_excluded_article_ids(db)
        self.assertNotIn(1, result, "needs_review articles should NOT be excluded")
        db.close()

    def test_disabled_plus_quarantined_both_excluded(self):
        """Disabled AND quarantined articles are both excluded (union)."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 0},  # disabled
            {"id": 2, "enabled": 1},  # quarantined
            {"id": 3, "enabled": 1},  # clean
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 2, "status": "quarantined"},
            {"kb_item_id": 3, "status": "approved"},
        ])
        result = compute_excluded_article_ids(db)
        self.assertIn(1, result, "Disabled article should be excluded")
        self.assertIn(2, result, "Quarantined article should be excluded")
        self.assertNotIn(3, result, "Approved article should be included")
        db.close()

    def test_caller_extra_excludes_merged(self):
        """Extra caller-supplied IDs are merged into the exclusion set."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1},
            {"id": 2, "enabled": 1},
            {"id": 3, "enabled": 1},
        ])
        result = compute_excluded_article_ids(db, extra_exclude_ids={2, 3})
        self.assertIn(2, result)
        self.assertIn(3, result)
        self.assertNotIn(1, result)
        db.close()

    def test_hard_rules_run_before_validation(self):
        """Disabled articles are excluded even if they have approved validation status.

        This confirms hard system rules take precedence over validation status.
        """
        db = self.SessionLocal()
        _seed_articles(db, [{"id": 1, "enabled": 0}])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
        ])
        result = compute_excluded_article_ids(db)
        self.assertIn(1, result, "Disabled article must be excluded even with approved status")
        db.close()


class TestGetExclusionLog(unittest.TestCase):
    """Tests for get_exclusion_log() — audit/logging helper."""

    def setUp(self):
        self.engine = _make_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_empty_excluded_ids(self):
        db = self.SessionLocal()
        entries = get_exclusion_log(db, frozenset())
        self.assertEqual(entries, [])
        db.close()

    def test_reason_codes_correct(self):
        """Each excluded ID gets the correct reason code."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 0},
            {"id": 2, "enabled": 1},
            {"id": 3, "enabled": 1},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 2, "status": "quarantined"},
            {"kb_item_id": 3, "status": "rejected"},
        ])
        excluded = frozenset({1, 2, 3, 99})
        entries = get_exclusion_log(db, excluded)
        reasons = {e["article_id"]: e["reason"] for e in entries}
        self.assertEqual(reasons[1], REASON_DISABLED)
        self.assertEqual(reasons[2], REASON_QUARANTINED)
        self.assertEqual(reasons[3], REASON_REJECTED)
        self.assertEqual(reasons[99], REASON_CALLER_EXCLUDED)
        db.close()


class TestFilterFusedResults(unittest.TestCase):
    """Tests for filter_fused_results() — post-fusion defense-in-depth."""

    def test_no_excluded_ids(self):
        fused = [1, 2, 3, 4, 5]
        result = filter_fused_results(fused, frozenset())
        self.assertEqual(result, [1, 2, 3, 4, 5])

    def test_excluded_ids_removed(self):
        fused = [1, 2, 3, 4, 5]
        result = filter_fused_results(fused, frozenset({2, 4}))
        self.assertEqual(result, [1, 3, 5])

    def test_all_excluded(self):
        fused = [1, 2, 3]
        result = filter_fused_results(fused, frozenset({1, 2, 3}))
        self.assertEqual(result, [])

    def test_no_overlap(self):
        fused = [1, 2, 3]
        result = filter_fused_results(fused, frozenset({10, 20}))
        self.assertEqual(result, [1, 2, 3])

    def test_empty_fused_list(self):
        result = filter_fused_results([], frozenset({1, 2}))
        self.assertEqual(result, [])

    def test_preserves_order(self):
        """Fused result ordering is preserved after filtering."""
        fused = [5, 3, 1, 4, 2]
        result = filter_fused_results(fused, frozenset({3, 2}))
        self.assertEqual(result, [5, 1, 4])


class TestLexicalPathFiltering(unittest.TestCase):
    """Integration test: lexical search respects filter policy."""

    def setUp(self):
        self.engine = _make_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_quarantined_excluded_from_lexical(self):
        """Quarantined articles should not appear in lexical search results."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1, "question": "Where is the food hall?",
             "answer": "The food hall is in building A."},
            {"id": 2, "enabled": 1, "question": "What food is available?",
             "answer": "Rice and soup are available."},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "quarantined"},
        ])

        # Reset lexical index cache
        from hub.retrieval.lexical import invalidate_lexical_index, lexical_search
        invalidate_lexical_index()

        result = lexical_search("food", db, top_k=5)
        result_ids = [r.article_id for r in result.results]

        self.assertIn(1, result_ids, "Approved article should appear in results")
        self.assertNotIn(2, result_ids, "Quarantined article should NOT appear in results")
        db.close()

    def test_rejected_excluded_from_lexical(self):
        """Rejected articles should not appear in lexical search results."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1, "question": "Where is the medical station?",
             "answer": "Building B, first floor."},
            {"id": 2, "enabled": 1, "question": "Medical hours?",
             "answer": "Open 24 hours."},
        ])
        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "rejected"},
        ])

        from hub.retrieval.lexical import invalidate_lexical_index, lexical_search
        invalidate_lexical_index()

        result = lexical_search("medical", db, top_k=5)
        result_ids = [r.article_id for r in result.results]

        self.assertIn(1, result_ids, "Approved article should appear in results")
        self.assertNotIn(2, result_ids, "Rejected article should NOT appear in results")
        db.close()

    def test_disabled_excluded_from_lexical(self):
        """Disabled articles should not appear in lexical search results."""
        db = self.SessionLocal()
        _seed_articles(db, [
            {"id": 1, "enabled": 1, "question": "Bus schedule?",
             "answer": "Every 2 hours."},
            {"id": 2, "enabled": 0, "question": "Bus route?",
             "answer": "Route A and B."},
        ])

        from hub.retrieval.lexical import invalidate_lexical_index, lexical_search
        invalidate_lexical_index()

        result = lexical_search("bus", db, top_k=5)
        result_ids = [r.article_id for r in result.results]

        self.assertIn(1, result_ids, "Enabled article should appear")
        self.assertNotIn(2, result_ids, "Disabled article should NOT appear")
        db.close()


class TestVectorPathFiltering(unittest.TestCase):
    """Test that the vector corpus loading respects filter policy."""

    def setUp(self):
        self.engine = _make_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_quarantined_not_in_corpus(self):
        """Quarantined articles should be excluded from the vector corpus."""
        db = self.SessionLocal()

        # Create articles with dummy embeddings
        import numpy as np
        from hub.retrieval.embedder import serialize_embedding

        art1 = schema.KBArticle(
            id=1, question="Q1", answer="A1", category="General",
            enabled=1, created_at=1, last_updated=1,
            embedding=serialize_embedding(np.random.rand(384).astype(np.float32)),
        )
        art2 = schema.KBArticle(
            id=2, question="Q2", answer="A2", category="General",
            enabled=1, created_at=1, last_updated=1,
            embedding=serialize_embedding(np.random.rand(384).astype(np.float32)),
        )
        db.add_all([art1, art2])
        db.commit()

        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "quarantined"},
        ])

        # Call _load_corpus with the exclusion set
        from hub.retrieval.search import _load_corpus, invalidate_corpus_cache
        invalidate_corpus_cache()

        excluded = compute_excluded_article_ids(db)
        corpus = _load_corpus(db, excluded_ids=excluded)

        article_ids = [a["id"] for a in corpus["articles"]]
        self.assertIn(1, article_ids, "Approved article should be in corpus")
        self.assertNotIn(2, article_ids, "Quarantined article should NOT be in corpus")
        db.close()

    def test_rejected_not_in_corpus(self):
        """Rejected articles should be excluded from the vector corpus."""
        db = self.SessionLocal()

        import numpy as np
        from hub.retrieval.embedder import serialize_embedding

        art1 = schema.KBArticle(
            id=1, question="Q1", answer="A1", category="General",
            enabled=1, created_at=1, last_updated=1,
            embedding=serialize_embedding(np.random.rand(384).astype(np.float32)),
        )
        art2 = schema.KBArticle(
            id=2, question="Q2", answer="A2", category="General",
            enabled=1, created_at=1, last_updated=1,
            embedding=serialize_embedding(np.random.rand(384).astype(np.float32)),
        )
        db.add_all([art1, art2])
        db.commit()

        _seed_validation_status(db, [
            {"kb_item_id": 1, "status": "approved"},
            {"kb_item_id": 2, "status": "rejected"},
        ])

        from hub.retrieval.search import _load_corpus, invalidate_corpus_cache
        invalidate_corpus_cache()

        excluded = compute_excluded_article_ids(db)
        corpus = _load_corpus(db, excluded_ids=excluded)

        article_ids = [a["id"] for a in corpus["articles"]]
        self.assertIn(1, article_ids, "Approved article should be in corpus")
        self.assertNotIn(2, article_ids, "Rejected article should NOT be in corpus")
        db.close()


class TestHybridFusedResultFiltering(unittest.TestCase):
    """Test that post-fusion filtering catches excluded articles."""

    def test_fused_results_filtered(self):
        """After fusion, excluded IDs are removed from the ranked list."""
        fused = [10, 20, 30, 40, 50]
        excluded = frozenset({20, 40})
        result = filter_fused_results(fused, excluded)
        self.assertEqual(result, [10, 30, 50])
        self.assertEqual(len(result), 3)

    def test_fused_results_no_excluded_articles(self):
        """When no articles are excluded, fused results pass through unchanged."""
        fused = [10, 20, 30]
        result = filter_fused_results(fused, frozenset())
        self.assertEqual(result, [10, 20, 30])

    def test_log_warning_on_caught_articles(self):
        """A warning is logged when post-fusion defense catches excluded articles."""
        fused = [1, 2, 3]
        excluded = frozenset({2})
        with self.assertLogs("hub.retrieval.filter_policy", level="WARNING") as cm:
            filter_fused_results(fused, excluded)
        self.assertTrue(
            any("post_fusion_defense" in msg for msg in cm.output),
            "Expected a warning log about post_fusion_defense",
        )


if __name__ == "__main__":
    unittest.main()
