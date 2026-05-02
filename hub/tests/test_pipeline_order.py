"""
hub/tests/test_pipeline_order.py

Unit tests for QueryPipeline stage ordering.

These tests verify the canonical pipeline order:
  normalize → intent → retrieve → clarification_gate → [rewrite → retrieve_retry]

All external dependencies (search.retrieve, rewriter.maybe_rewrite,
search._intent_classifier) are mocked so no real DB, embedder, or LLM is needed.
"""

import unittest
from unittest.mock import MagicMock, patch

from hub.retrieval.pipeline import (
    QueryPipeline,
    STAGE_NORMALIZE,
    STAGE_INTENT,
    STAGE_RETRIEVE,
    STAGE_CLARIFICATION_GATE,
    STAGE_REWRITE,
    STAGE_RETRIEVE_RETRY,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_result(answer_type: str, confidence: float = 0.85) -> dict:
    """Build a minimal retrieve() result dict."""
    return {
        "answer_text": "Test answer.",
        "answer_type": answer_type,
        "confidence": confidence,
        "source_id": 1,
        "categories": None,
        "article_data": {"question": "Q", "answer": "A", "category": "food", "tags": []},
        "intent": "food",
        "intent_confidence": 0.75,
        "follow_up_prompt": None,
        "follow_up_intent": None,
    }


def _make_clarification_result() -> dict:
    return {
        "answer_text": "Please clarify.",
        "answer_type": "NEEDS_CLARIFICATION",
        "confidence": 0.42,
        "source_id": None,
        "categories": ["food", "medical"],
        "article_data": None,
        "intent": "unclear",
        "intent_confidence": 0.20,
        "follow_up_prompt": None,
        "follow_up_intent": None,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPipelineStageOrder(unittest.TestCase):

    def setUp(self):
        self.db = MagicMock()

    # -- AC1 + AC2: Normal text query runs through all non-clarification stages
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_normal_query_stage_order(self, mock_retrieve, mock_rewrite):
        """
        For a normal query that gets a DIRECT_MATCH, the pipeline must execute:
          normalize → intent → retrieve → clarification_gate → rewrite
        (no retrieve_retry because rewrite returns unchanged text)

        Note: normalize_query("where is medical") → "where is the medical area"
        We use a query whose normalized form is stable for this test.
        mock_rewrite must return the *normalized* text so that rewrite_happened=False.
        """
        mock_retrieve.return_value = _make_result("DIRECT_MATCH")
        # normalize_query("registration") → "registration" (no correction entry)
        mock_rewrite.return_value = "registration"  # same as normalized — no change

        result = QueryPipeline().run(self.db, "registration", is_retry=False)

        # Stage order check
        self.assertEqual(
            result.stage_log,
            [STAGE_NORMALIZE, STAGE_INTENT, STAGE_RETRIEVE, STAGE_CLARIFICATION_GATE, STAGE_REWRITE],
            "Stage log must follow canonical order for a normal query with no rewrite.",
        )
        self.assertEqual(result.retrieve_result["answer_type"], "DIRECT_MATCH")
        self.assertFalse(result.rewrite_happened)
        # retrieve called exactly once
        mock_retrieve.assert_called_once()

    # -- AC3: Rewrite does not run before the clarification decision
    # -- AC4: Retrieval does not run when clarification is required
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_clarification_stops_pipeline_before_rewrite(self, mock_retrieve, mock_rewrite):
        """
        When retrieve returns NEEDS_CLARIFICATION, the pipeline must:
          - Stop at clarification_gate
          - NOT call maybe_rewrite
          - NOT call retrieve a second time
        """
        mock_retrieve.return_value = _make_clarification_result()

        result = QueryPipeline().run(self.db, "i need help", is_retry=False)

        # Stage log must end at clarification_gate — no rewrite, no retry
        self.assertEqual(
            result.stage_log,
            [STAGE_NORMALIZE, STAGE_INTENT, STAGE_RETRIEVE, STAGE_CLARIFICATION_GATE],
            "Pipeline must stop at clarification_gate; rewrite and retrieve_retry must not appear.",
        )
        # Rewrite must not have been called
        mock_rewrite.assert_not_called()
        # Retrieve must have been called exactly once (no second pass)
        mock_retrieve.assert_called_once()
        # Result preserved
        self.assertEqual(result.retrieve_result["answer_type"], "NEEDS_CLARIFICATION")
        self.assertFalse(result.rewrite_happened)

    # -- AC2 + verify rewrite fires only after clarification check passes
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_rewrite_runs_only_after_clarification_gate(self, mock_retrieve, mock_rewrite):
        """
        When the first retrieve returns NO_MATCH (no clarification needed),
        rewrite may run. If it produces a different query, a second retrieve
        is called. Stage log must include retrieve_retry.
        """
        # First retrieve: NO_MATCH (triggers rewrite path)
        no_match_result = _make_result("NO_MATCH", confidence=0.15)
        no_match_result["intent"] = "unclear"
        no_match_result["intent_confidence"] = 0.10

        # Second retrieve (after rewrite): DIRECT_MATCH
        direct_result = _make_result("DIRECT_MATCH")
        mock_retrieve.side_effect = [no_match_result, direct_result]

        # Rewrite produces a different query
        mock_rewrite.return_value = "where can i get food"

        result = QueryPipeline().run(self.db, "i dont know ugh food", is_retry=False)

        expected_stages = [
            STAGE_NORMALIZE,
            STAGE_INTENT,
            STAGE_RETRIEVE,
            STAGE_CLARIFICATION_GATE,
            STAGE_REWRITE,
            STAGE_RETRIEVE_RETRY,
        ]
        self.assertEqual(
            result.stage_log,
            expected_stages,
            "Stage log must include retrieve_retry when rewrite produces a different query.",
        )
        self.assertTrue(result.rewrite_happened)
        self.assertEqual(result.rewritten_text, "where can i get food")
        self.assertEqual(result.retrieve_result["answer_type"], "DIRECT_MATCH")
        # retrieve called twice
        self.assertEqual(mock_retrieve.call_count, 2)

    # -- Verify rewrite does NOT trigger a second retrieval if text is unchanged
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_no_second_retrieve_when_rewrite_unchanged(self, mock_retrieve, mock_rewrite):
        """
        If maybe_rewrite returns the same text as the normalized query (no change),
        retrieve_retry must not be called.

        normalize_query("registration") → "registration" (no correction mapping).
        We return that same string from the mock to simulate a no-op rewrite.
        """
        mock_retrieve.return_value = _make_result("NO_MATCH", confidence=0.20)
        mock_rewrite.return_value = "registration"  # same as normalized

        result = QueryPipeline().run(self.db, "registration", is_retry=False)

        self.assertNotIn(STAGE_RETRIEVE_RETRY, result.stage_log)
        self.assertFalse(result.rewrite_happened)
        mock_retrieve.assert_called_once()

    # -- Verify normalize always runs first
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_normalize_is_first_stage(self, mock_retrieve, mock_rewrite):
        mock_retrieve.return_value = _make_result("DIRECT_MATCH")
        mock_rewrite.return_value = "test query"

        result = QueryPipeline().run(self.db, "TEST QUERY  ", is_retry=False)

        self.assertEqual(result.stage_log[0], STAGE_NORMALIZE)
        # Normalize lowercases and strips
        self.assertEqual(result.normalized_text, "test query")

    # -- Verify intent always runs before retrieve
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_intent_runs_before_retrieve(self, mock_retrieve, mock_rewrite):
        mock_retrieve.return_value = _make_result("DIRECT_MATCH")
        mock_rewrite.return_value = "some query"

        result = QueryPipeline().run(self.db, "some query", is_retry=False)

        intent_idx = result.stage_log.index(STAGE_INTENT)
        retrieve_idx = result.stage_log.index(STAGE_RETRIEVE)
        self.assertLess(
            intent_idx, retrieve_idx,
            "STAGE_INTENT must appear before STAGE_RETRIEVE in stage_log.",
        )

    # -- Verify clarification_gate always runs before rewrite
    @patch("hub.retrieval.pipeline.query_rewriter.maybe_rewrite")
    @patch("hub.retrieval.pipeline.search.retrieve")
    @patch("hub.retrieval.pipeline.search._intent_classifier", None)
    def test_clarification_gate_runs_before_rewrite(self, mock_retrieve, mock_rewrite):
        mock_retrieve.return_value = _make_result("DIRECT_MATCH")
        mock_rewrite.return_value = "some query"

        result = QueryPipeline().run(self.db, "some query", is_retry=False)

        gate_idx = result.stage_log.index(STAGE_CLARIFICATION_GATE)
        rewrite_idx = result.stage_log.index(STAGE_REWRITE)
        self.assertLess(
            gate_idx, rewrite_idx,
            "STAGE_CLARIFICATION_GATE must appear before STAGE_REWRITE in stage_log.",
        )


if __name__ == "__main__":
    unittest.main()
