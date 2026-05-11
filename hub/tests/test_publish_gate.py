"""
hub/tests/test_publish_gate.py

Unit tests for the KB publish validation gate (Slice 3 Story 3).

Tests verify that publish_kb correctly:
  - blocks when quarantined items exist under strict policy
  - proceeds with warning status when only needs_review items exist
  - proceeds with pass status when all items are approved
  - skips validation when gate policy is 'off'
  - never writes to DB or bumps kb_version when blocked
"""

import unittest
from unittest.mock import MagicMock, patch, call

from fastapi import HTTPException

from hub.validation.metadata import (
    PublishGateHandoff,
    PUBLISH_STATUS_BLOCKED,
    PUBLISH_STATUS_WARNING,
    PUBLISH_STATUS_PASS,
)


def _make_handoff(status: str, blocked: bool, quarantined: int = 0, needs_review: int = 0) -> PublishGateHandoff:
    failure_reasons = (f"article:1:taxonomy.primary_assignment_missing:error",) if blocked else ()
    return PublishGateHandoff(
        status=status,
        blocked=blocked,
        summary_counts={
            "total_items": quarantined + needs_review + (1 if status == PUBLISH_STATUS_PASS else 0),
            "approved": 1 if status == PUBLISH_STATUS_PASS else 0,
            "needs_review": needs_review,
            "quarantined": quarantined,
            "failed_rules": quarantined + needs_review,
        },
        failure_reasons=failure_reasons,
    )


class TestPublishGate(unittest.TestCase):

    def _run_publish(self, gate_policy: str, handoff: PublishGateHandoff):
        """Run publish_kb with mocked DB and mocked validation layer."""
        from hub.api import routes_admin

        mock_db = MagicMock()
        mock_article = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_article]

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 64

        with (
            patch.object(routes_admin, "_get_structured_config_value", return_value=gate_policy),
            patch("hub.api.routes_admin.load_validation_targets", return_value=()),
            patch("hub.api.routes_admin.load_taxonomy_reference", return_value=(frozenset(), frozenset())),
            patch("hub.api.routes_admin.validate_metadata", return_value=MagicMock()),
            patch("hub.api.routes_admin.build_publish_gate_handoff", return_value=handoff),
            patch("hub.api.routes_admin.load_embedder", return_value=mock_embedder),
            patch("hub.api.routes_admin.serialize_embedding", return_value=b"vec"),
            patch("hub.api.routes_admin.get_embeddable_text", return_value="text"),
            patch("hub.api.routes_admin._increment_kb_version") as mock_bump,
            patch("hub.api.routes_admin.invalidate_corpus_cache") as mock_invalidate,
        ):
            import asyncio
            try:
                result = asyncio.get_event_loop().run_until_complete(
                    routes_admin.publish_kb(db=mock_db)
                )
                return result, mock_bump, mock_invalidate, None
            except HTTPException as exc:
                return None, mock_bump, mock_invalidate, exc

    # -----------------------------------------------------------------------
    # Strict policy — blocked (quarantined items)
    # -----------------------------------------------------------------------

    def test_strict_blocked_raises_422(self):
        handoff = _make_handoff(PUBLISH_STATUS_BLOCKED, blocked=True, quarantined=1)
        _, _, _, exc = self._run_publish("strict", handoff)

        self.assertIsNotNone(exc)
        self.assertEqual(exc.status_code, 422)

    def test_strict_blocked_response_contains_validation_gate(self):
        handoff = _make_handoff(PUBLISH_STATUS_BLOCKED, blocked=True, quarantined=2)
        _, _, _, exc = self._run_publish("strict", handoff)

        detail = exc.detail
        self.assertIn("validation_gate", detail)
        self.assertEqual(detail["validation_gate"]["status"], PUBLISH_STATUS_BLOCKED)
        self.assertEqual(detail["validation_gate"]["summary_counts"]["quarantined"], 2)
        self.assertTrue(len(detail["validation_gate"]["failure_reasons"]) > 0)

    def test_strict_blocked_does_not_bump_kb_version(self):
        handoff = _make_handoff(PUBLISH_STATUS_BLOCKED, blocked=True, quarantined=1)
        _, mock_bump, _, _ = self._run_publish("strict", handoff)

        mock_bump.assert_not_called()

    def test_strict_blocked_does_not_invalidate_corpus_cache(self):
        handoff = _make_handoff(PUBLISH_STATUS_BLOCKED, blocked=True, quarantined=1)
        _, _, mock_invalidate, _ = self._run_publish("strict", handoff)

        mock_invalidate.assert_not_called()

    # -----------------------------------------------------------------------
    # Strict policy — warning (needs_review items only)
    # -----------------------------------------------------------------------

    def test_strict_warning_proceeds_and_returns_warning_status(self):
        handoff = _make_handoff(PUBLISH_STATUS_WARNING, blocked=False, needs_review=1)
        result, _, _, exc = self._run_publish("strict", handoff)

        self.assertIsNone(exc)
        self.assertIsNotNone(result)
        self.assertEqual(result["validation_gate"]["status"], PUBLISH_STATUS_WARNING)

    def test_strict_warning_bumps_kb_version(self):
        handoff = _make_handoff(PUBLISH_STATUS_WARNING, blocked=False, needs_review=1)
        _, mock_bump, _, _ = self._run_publish("strict", handoff)

        mock_bump.assert_called_once()

    # -----------------------------------------------------------------------
    # Strict policy — pass (all approved)
    # -----------------------------------------------------------------------

    def test_strict_pass_returns_published_status_and_pass_gate(self):
        handoff = _make_handoff(PUBLISH_STATUS_PASS, blocked=False)
        result, _, _, exc = self._run_publish("strict", handoff)

        self.assertIsNone(exc)
        self.assertEqual(result["status"], "published")
        self.assertEqual(result["validation_gate"]["status"], PUBLISH_STATUS_PASS)

    def test_strict_pass_bumps_kb_version(self):
        handoff = _make_handoff(PUBLISH_STATUS_PASS, blocked=False)
        _, mock_bump, _, _ = self._run_publish("strict", handoff)

        mock_bump.assert_called_once()

    # -----------------------------------------------------------------------
    # warn_only policy — blocked handoff still proceeds
    # -----------------------------------------------------------------------

    def test_warn_only_blocked_handoff_still_proceeds(self):
        handoff = _make_handoff(PUBLISH_STATUS_BLOCKED, blocked=True, quarantined=1)
        result, _, _, exc = self._run_publish("warn_only", handoff)

        self.assertIsNone(exc)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "published")

    def test_warn_only_includes_validation_gate_in_response(self):
        handoff = _make_handoff(PUBLISH_STATUS_BLOCKED, blocked=True, quarantined=1)
        result, _, _, exc = self._run_publish("warn_only", handoff)

        self.assertIn("validation_gate", result)
        self.assertEqual(result["validation_gate"]["status"], PUBLISH_STATUS_BLOCKED)

    # -----------------------------------------------------------------------
    # off policy — validation skipped entirely
    # -----------------------------------------------------------------------

    def test_off_policy_skips_validation(self):
        from hub.api import routes_admin

        mock_db = MagicMock()
        mock_article = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_article]

        mock_embedder = MagicMock()
        mock_embedder.embed_text.return_value = [0.1] * 64

        called_validation = []

        def record_call(*args, **kwargs):
            called_validation.append(True)
            return ()

        with (
            patch.object(routes_admin, "_get_structured_config_value", return_value="off"),
            patch("hub.api.routes_admin.load_validation_targets", side_effect=record_call),
            patch("hub.api.routes_admin.load_embedder", return_value=mock_embedder),
            patch("hub.api.routes_admin.serialize_embedding", return_value=b"vec"),
            patch("hub.api.routes_admin.get_embeddable_text", return_value="text"),
            patch("hub.api.routes_admin._increment_kb_version"),
            patch("hub.api.routes_admin.invalidate_corpus_cache"),
        ):
            import asyncio
            asyncio.get_event_loop().run_until_complete(routes_admin.publish_kb(db=mock_db))

        self.assertEqual(len(called_validation), 0, "Validation should not run when policy is 'off'")

    def test_off_policy_returns_none_validation_gate(self):
        from hub.api import routes_admin

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with (
            patch.object(routes_admin, "_get_structured_config_value", return_value="off"),
            patch("hub.api.routes_admin.load_embedder", return_value=MagicMock()),
            patch("hub.api.routes_admin._increment_kb_version"),
            patch("hub.api.routes_admin.invalidate_corpus_cache"),
        ):
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(routes_admin.publish_kb(db=mock_db))

        self.assertIsNone(result["validation_gate"])


if __name__ == "__main__":
    unittest.main()
