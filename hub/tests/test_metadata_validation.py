import unittest

from hub.validation import metadata


def _make_target(
    article_id: int = 1,
    question: str = "Where is the medical station?",
    category: str = "medical",
    tags: tuple[str, ...] = ("clinic", "doctor"),
    authority: str | None = "official",
    scope: str | None = "shelter_local",
    taxonomy_node_ids: tuple[str, ...] = ("rk.tax.health_medical.medical_services",),
) -> metadata.MetadataValidationTarget:
    return metadata.MetadataValidationTarget(
        article_id=article_id,
        question=question,
        category=category,
        tags=tags,
        authority=authority,
        scope=scope,
        taxonomy_node_ids=taxonomy_node_ids,
    )


class TestMetadataValidation(unittest.TestCase):
    def setUp(self):
        self.known_node_ids = {
            "rk.tax.health_medical.medical_services",
            "rk.tax.food_water.meals",
        }
        self.active_node_ids = {
            "rk.tax.health_medical.medical_services",
            "rk.tax.food_water.meals",
        }

    def test_valid_target_is_approved(self):
        target = _make_target()

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        self.assertEqual(result.summary.publish_status, metadata.PUBLISH_STATUS_PASS)
        self.assertEqual(result.summary.approved_count, 1)
        self.assertEqual(result.items[0].status, metadata.STATUS_APPROVED)
        self.assertEqual(len(result.items[0].rule_results), 10)
        self.assertTrue(all(rule.passed for rule in result.items[0].rule_results))

    def test_missing_taxonomy_quarantines_item_and_blocks_publish(self):
        target = _make_target(taxonomy_node_ids=())

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        failed_rule_ids = {rule.rule_id for rule in result.items[0].failed_rules}
        self.assertEqual(result.items[0].status, metadata.STATUS_QUARANTINED)
        self.assertEqual(result.summary.publish_status, metadata.PUBLISH_STATUS_BLOCKED)
        self.assertIn(metadata.RULE_TAXONOMY_PRIMARY_ASSIGNMENT_MISSING, failed_rule_ids)

    def test_unknown_taxonomy_node_quarantines_item(self):
        target = _make_target(taxonomy_node_ids=("rk.tax.unknown",))

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        failed_rule_ids = {rule.rule_id for rule in result.items[0].failed_rules}
        self.assertEqual(result.items[0].status, metadata.STATUS_QUARANTINED)
        self.assertIn(metadata.RULE_TAXONOMY_ASSIGNMENT_UNKNOWN_NODE, failed_rule_ids)

    def test_invalid_authority_quarantines_item(self):
        target = _make_target(authority="city_official")

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        failed_rule_ids = {rule.rule_id for rule in result.items[0].failed_rules}
        self.assertEqual(result.items[0].status, metadata.STATUS_QUARANTINED)
        self.assertIn(metadata.RULE_METADATA_AUTHORITY_INVALID, failed_rule_ids)

    def test_invalid_scope_quarantines_item(self):
        target = _make_target(scope="regional")

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        failed_rule_ids = {rule.rule_id for rule in result.items[0].failed_rules}
        self.assertEqual(result.items[0].status, metadata.STATUS_QUARANTINED)
        self.assertIn(metadata.RULE_METADATA_SCOPE_INVALID, failed_rule_ids)

    def test_missing_metadata_only_needs_review(self):
        target = _make_target(authority=None, scope=None)

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        failed_rule_ids = {rule.rule_id for rule in result.items[0].failed_rules}
        self.assertEqual(result.items[0].status, metadata.STATUS_NEEDS_REVIEW)
        self.assertEqual(result.summary.publish_status, metadata.PUBLISH_STATUS_WARNING)
        self.assertIn(metadata.RULE_METADATA_AUTHORITY_MISSING, failed_rule_ids)
        self.assertIn(metadata.RULE_METADATA_SCOPE_MISSING, failed_rule_ids)

    def test_empty_or_placeholder_labels_need_review(self):
        target = _make_target(question="  ", category="placeholder", tags=("x",))

        result = metadata.validate_metadata(
            targets=[target],
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        failed_rule_ids = {rule.rule_id for rule in result.items[0].failed_rules}
        self.assertEqual(result.items[0].status, metadata.STATUS_NEEDS_REVIEW)
        self.assertIn(metadata.RULE_CONTENT_LABEL_EMPTY, failed_rule_ids)
        self.assertIn(metadata.RULE_CONTENT_LABEL_PLACEHOLDER, failed_rule_ids)
        self.assertIn(metadata.RULE_CONTENT_LABEL_TOO_SHORT, failed_rule_ids)

    def test_results_are_deterministic_for_same_snapshot(self):
        targets = [
            _make_target(article_id=2, category="food", tags=("meals",)),
            _make_target(article_id=1),
        ]

        first_result = metadata.validate_metadata(
            targets=targets,
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )
        second_result = metadata.validate_metadata(
            targets=targets,
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        self.assertEqual(first_result, second_result)
        self.assertEqual([item.article_id for item in first_result.items], [1, 2])

    def test_publish_gate_handoff_reports_blocked_status_and_reasons(self):
        targets = [
            _make_target(article_id=1),
            _make_target(article_id=2, taxonomy_node_ids=()),
        ]
        result = metadata.validate_metadata(
            targets=targets,
            known_taxonomy_node_ids=self.known_node_ids,
            active_taxonomy_node_ids=self.active_node_ids,
        )

        handoff = metadata.build_publish_gate_handoff(result)

        self.assertTrue(handoff.blocked)
        self.assertEqual(handoff.status, metadata.PUBLISH_STATUS_BLOCKED)
        self.assertEqual(handoff.summary_counts["quarantined"], 1)
        self.assertTrue(
            any(
                metadata.RULE_TAXONOMY_PRIMARY_ASSIGNMENT_MISSING in reason
                for reason in handoff.failure_reasons
            )
        )


if __name__ == "__main__":
    unittest.main()
