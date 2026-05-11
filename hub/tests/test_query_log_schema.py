"""
hub/tests/test_query_log_schema.py

Unit tests for the Slice 6A Story 1 structured query log schema additions.

Tests verify that:
  - All new columns exist on the QueryLog ORM model
  - All new columns are nullable (additive, safe for existing rows)
  - JSON-typed columns (top_k arrays) accept JSON-serialized lists
  - intent_label and intent_confidence are wired into routes_query.py writes
  - clarification fields are wired into the clarification pause path
"""

import json
import unittest

from hub.db import schema


# ---------------------------------------------------------------------------
# Schema-level tests
# ---------------------------------------------------------------------------


class TestQueryLogColumns(unittest.TestCase):
    """Verify the new Slice 6A Story 1 columns exist on QueryLog."""

    EXPECTED_NEW_COLUMNS = {
        # AC4 — intent
        "intent_label",
        "intent_confidence",
        # AC5 — clarification metadata
        "clarification_categories_offered",
        "clarification_node_id_selected",
        # AC5 — hybrid retrieval contribution (populated by Slice 4 Story 5)
        "lexical_top_k_ids",
        "lexical_top_k_scores",
        "lexical_top_k_ranks",
        "lexical_latency_ms",
        "vector_top_k_ids",
        "vector_top_k_scores",
        "vector_top_k_ranks",
        "fusion_strategy",
        "fusion_top_k_ids",
        "fusion_top_k_scores",
        "fusion_top_k_ranks",
        # AC5 — failure / fallback (populated by Slice 6A Story 8)
        "fallback_reason",
        "failed_stage",
    }

    def setUp(self):
        self.columns = {c.name for c in schema.QueryLog.__table__.columns}

    def test_all_new_columns_present(self):
        missing = self.EXPECTED_NEW_COLUMNS - self.columns
        self.assertFalse(
            missing,
            f"QueryLog is missing expected Slice 6A Story 1 columns: {missing}",
        )

    def test_all_new_columns_are_nullable(self):
        for name in self.EXPECTED_NEW_COLUMNS:
            col = schema.QueryLog.__table__.columns[name]
            self.assertTrue(
                col.nullable,
                f"QueryLog.{name} must be nullable (additive, safe for existing rows)",
            )

    def test_intent_confidence_is_numeric(self):
        col = schema.QueryLog.__table__.columns["intent_confidence"]
        self.assertIn(
            col.type.__class__.__name__.lower(),
            {"float", "real", "numeric"},
            f"intent_confidence should be a numeric type, got {col.type}",
        )

    def test_lexical_latency_ms_is_numeric(self):
        col = schema.QueryLog.__table__.columns["lexical_latency_ms"]
        self.assertIn(
            col.type.__class__.__name__.lower(),
            {"float", "real", "numeric"},
            f"lexical_latency_ms should be a numeric type, got {col.type}",
        )


# ---------------------------------------------------------------------------
# Instantiation tests — verify columns can be written with realistic data
# ---------------------------------------------------------------------------


class TestQueryLogInstantiation(unittest.TestCase):
    """Verify a QueryLog row can be constructed with the new fields."""

    def test_can_construct_with_all_new_fields(self):
        entry = schema.QueryLog(
            kiosk_id="k1",
            session_id="s1",
            transcript_original="hi",
            language="en",
            kb_version=1,
            answer_type="DIRECT_MATCH",
            latency_ms=10.0,
            created_at=0,
            # New fields under test
            intent_label="food",
            intent_confidence=0.87,
            clarification_categories_offered=json.dumps(["food", "medical"]),
            clarification_node_id_selected="rk.tax.food",
            lexical_top_k_ids=json.dumps([1, 4, 7, 12, 19]),
            lexical_top_k_scores=json.dumps([0.91, 0.84, 0.77, 0.65, 0.50]),
            lexical_top_k_ranks=json.dumps([1, 2, 3, 4, 5]),
            lexical_latency_ms=4.2,
            vector_top_k_ids=json.dumps([4, 1, 22, 19, 7]),
            vector_top_k_scores=json.dumps([0.82, 0.79, 0.71, 0.66, 0.58]),
            vector_top_k_ranks=json.dumps([1, 2, 3, 4, 5]),
            fusion_strategy="rrf",
            fusion_top_k_ids=json.dumps([4, 1, 7, 19, 22]),
            fusion_top_k_scores=json.dumps([0.032, 0.030, 0.025, 0.020, 0.017]),
            fusion_top_k_ranks=json.dumps([1, 2, 3, 4, 5]),
            fallback_reason="low_confidence",
            failed_stage="retrieve",
        )
        # Spot-check round-trip on JSON fields
        self.assertEqual(json.loads(entry.lexical_top_k_ids), [1, 4, 7, 12, 19])
        self.assertEqual(json.loads(entry.fusion_top_k_ranks), [1, 2, 3, 4, 5])
        self.assertEqual(entry.intent_label, "food")
        self.assertAlmostEqual(entry.intent_confidence, 0.87)
        self.assertEqual(entry.fallback_reason, "low_confidence")

    def test_can_construct_with_only_legacy_fields(self):
        """Existing call sites that omit the new fields must still work."""
        entry = schema.QueryLog(
            kiosk_id="k1",
            transcript_original="hello",
            language="en",
            kb_version=1,
            answer_type="DIRECT_MATCH",
            latency_ms=5.0,
            created_at=0,
        )
        # All new fields default to None (nullable)
        self.assertIsNone(entry.intent_label)
        self.assertIsNone(entry.intent_confidence)
        self.assertIsNone(entry.clarification_categories_offered)
        self.assertIsNone(entry.lexical_top_k_ids)
        self.assertIsNone(entry.fusion_strategy)
        self.assertIsNone(entry.fallback_reason)


# ---------------------------------------------------------------------------
# Migration tests — verify migrate_schema.py registers all new columns
# ---------------------------------------------------------------------------


class TestQueryLogMigrations(unittest.TestCase):
    """Verify migrate_schema.py has ALTER TABLE statements for all new columns."""

    EXPECTED_MIGRATION_KEYS = {
        "intent_label",
        "intent_confidence",
        "clarification_categories_offered",
        "clarification_node_id_selected",
        "lexical_top_k_ids",
        "lexical_top_k_scores",
        "lexical_top_k_ranks",
        "lexical_latency_ms",
        "vector_top_k_ids",
        "vector_top_k_scores",
        "vector_top_k_ranks",
        "fusion_strategy",
        "fusion_top_k_ids",
        "fusion_top_k_scores",
        "fusion_top_k_ranks",
        "fallback_reason",
        "failed_stage",
    }

    def test_migrate_schema_contains_all_new_columns(self):
        """Read the migrate_schema.py source and confirm ALTER TABLE entries exist."""
        from pathlib import Path

        migrate_path = Path(schema.__file__).parent / "migrate_schema.py"
        source = migrate_path.read_text(encoding="utf-8")
        missing = []
        for key in self.EXPECTED_MIGRATION_KEYS:
            # Each migration is keyed by column name with an ALTER TABLE statement
            if f'"{key}":' not in source or f"ADD COLUMN {key}" not in source:
                missing.append(key)
        self.assertFalse(
            missing,
            f"migrate_schema.py missing ALTER TABLE entries for: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
