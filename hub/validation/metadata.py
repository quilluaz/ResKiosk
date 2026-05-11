from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from hub.db import schema


ALLOWED_AUTHORITIES = frozenset({"official", "shelter_staff", "volunteer", "unknown"})
ALLOWED_SCOPES = frozenset({"shelter_local", "general"})
PLACEHOLDER_LABELS = frozenset(
    {
        "tbd",
        "todo",
        "n/a",
        "na",
        "none",
        "placeholder",
        "sample",
        "test",
        "lorem ipsum",
        "unknown",
    }
)

RULE_TAXONOMY_PRIMARY_ASSIGNMENT_MISSING = "taxonomy.primary_assignment_missing"
RULE_TAXONOMY_ASSIGNMENT_UNKNOWN_NODE = "taxonomy.assignment_unknown_node"
RULE_TAXONOMY_ASSIGNMENT_INACTIVE_NODE = "taxonomy.assignment_inactive_node"
RULE_METADATA_AUTHORITY_MISSING = "metadata.authority_missing"
RULE_METADATA_AUTHORITY_INVALID = "metadata.authority_invalid"
RULE_METADATA_SCOPE_MISSING = "metadata.scope_missing"
RULE_METADATA_SCOPE_INVALID = "metadata.scope_invalid"
RULE_CONTENT_LABEL_EMPTY = "content.label_empty"
RULE_CONTENT_LABEL_PLACEHOLDER = "content.label_placeholder"
RULE_CONTENT_LABEL_TOO_SHORT = "content.label_too_short"

SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
STATUS_APPROVED = "approved"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_QUARANTINED = "quarantined"
PUBLISH_STATUS_PASS = "pass"
PUBLISH_STATUS_WARNING = "warning"
PUBLISH_STATUS_BLOCKED = "blocked"


@dataclass(frozen=True)
class MetadataValidationTarget:
    article_id: int
    question: str | None
    category: str | None
    tags: tuple[str, ...] = ()
    authority: str | None = None
    scope: str | None = None
    taxonomy_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetadataRuleResult:
    rule_id: str
    severity: str
    passed: bool
    message: str


@dataclass(frozen=True)
class MetadataItemValidationResult:
    article_id: int
    status: str
    rule_results: tuple[MetadataRuleResult, ...]

    @property
    def failed_rules(self) -> tuple[MetadataRuleResult, ...]:
        return tuple(result for result in self.rule_results if not result.passed)


@dataclass(frozen=True)
class MetadataValidationSummary:
    total_items: int
    approved_count: int
    needs_review_count: int
    quarantined_count: int
    failed_rule_count: int
    publish_status: str


@dataclass(frozen=True)
class MetadataValidationRunResult:
    items: tuple[MetadataItemValidationResult, ...]
    summary: MetadataValidationSummary


@dataclass(frozen=True)
class PublishGateHandoff:
    status: str
    blocked: bool
    summary_counts: dict[str, int]
    failure_reasons: tuple[str, ...]


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _split_tags(raw_tags: str | None) -> tuple[str, ...]:
    if not raw_tags:
        return ()
    tags = tuple(tag.strip() for tag in raw_tags.split(",") if tag and tag.strip())
    return tuple(sorted(tags))


def load_validation_targets(db: Session) -> tuple[MetadataValidationTarget, ...]:
    """Load deterministic article validation targets for Story 1.

    Story 1 validates the current text KB (`kb_articles`) and Goal 7 taxonomy
    assignments only. This loader does not call any online services.
    """
    articles = (
        db.query(schema.KBArticle)
        .filter(schema.KBArticle.enabled == 1)
        .order_by(schema.KBArticle.id.asc())
        .all()
    )
    assignments = (
        db.query(schema.KBItemTaxonomy)
        .order_by(
            schema.KBItemTaxonomy.kb_item_id.asc(),
            schema.KBItemTaxonomy.taxonomy_node_id.asc(),
        )
        .all()
    )

    assignment_map: dict[int, list[str]] = {}
    for row in assignments:
        assignment_map.setdefault(row.kb_item_id, []).append(row.taxonomy_node_id)

    targets = []
    for article in articles:
        targets.append(
            MetadataValidationTarget(
                article_id=article.id,
                question=article.question,
                category=article.category,
                tags=_split_tags(article.tags),
                authority=article.authority,
                scope=article.scope,
                taxonomy_node_ids=tuple(sorted(assignment_map.get(article.id, []))),
            )
        )
    return tuple(targets)


def load_taxonomy_reference(db: Session) -> tuple[frozenset[str], frozenset[str]]:
    """Return known and active taxonomy node IDs for deterministic validation."""
    nodes = db.query(schema.TaxonomyNode).order_by(schema.TaxonomyNode.id.asc()).all()
    known_node_ids = frozenset(node.id for node in nodes)
    active_node_ids = frozenset(node.id for node in nodes if bool(node.is_active))
    return known_node_ids, active_node_ids


def validate_metadata(
    targets: Iterable[MetadataValidationTarget],
    known_taxonomy_node_ids: Iterable[str],
    active_taxonomy_node_ids: Iterable[str] | None = None,
) -> MetadataValidationRunResult:
    known_node_ids = frozenset(known_taxonomy_node_ids)
    active_node_ids = frozenset(active_taxonomy_node_ids or ())

    item_results = []
    for target in sorted(targets, key=lambda item: item.article_id):
        item_results.append(_validate_target(target, known_node_ids, active_node_ids))

    item_results_tuple = tuple(item_results)
    summary = _summarize_results(item_results_tuple)
    return MetadataValidationRunResult(items=item_results_tuple, summary=summary)


def build_publish_gate_handoff(result: MetadataValidationRunResult) -> PublishGateHandoff:
    failure_reasons = []
    for item in result.items:
        for rule in item.failed_rules:
            failure_reasons.append(
                f"article:{item.article_id}:{rule.rule_id}:{rule.severity}"
            )

    return PublishGateHandoff(
        status=result.summary.publish_status,
        blocked=result.summary.publish_status == PUBLISH_STATUS_BLOCKED,
        summary_counts={
            "total_items": result.summary.total_items,
            "approved": result.summary.approved_count,
            "needs_review": result.summary.needs_review_count,
            "quarantined": result.summary.quarantined_count,
            "failed_rules": result.summary.failed_rule_count,
        },
        failure_reasons=tuple(failure_reasons),
    )


def _validate_target(
    target: MetadataValidationTarget,
    known_node_ids: frozenset[str],
    active_node_ids: frozenset[str],
) -> MetadataItemValidationResult:
    results = (
        _check_taxonomy_presence(target),
        _check_taxonomy_known(target, known_node_ids),
        _check_taxonomy_active(target, active_node_ids),
        _check_authority_missing(target),
        _check_authority_invalid(target),
        _check_scope_missing(target),
        _check_scope_invalid(target),
        _check_label_empty(target),
        _check_label_placeholder(target),
        _check_label_too_short(target),
    )

    status = _derive_item_status(results)
    return MetadataItemValidationResult(
        article_id=target.article_id,
        status=status,
        rule_results=results,
    )


def _derive_item_status(rule_results: tuple[MetadataRuleResult, ...]) -> str:
    if any((not result.passed) and result.severity == SEVERITY_ERROR for result in rule_results):
        return STATUS_QUARANTINED
    if any(not result.passed for result in rule_results):
        return STATUS_NEEDS_REVIEW
    return STATUS_APPROVED


def _summarize_results(
    item_results: tuple[MetadataItemValidationResult, ...],
) -> MetadataValidationSummary:
    approved_count = sum(1 for item in item_results if item.status == STATUS_APPROVED)
    needs_review_count = sum(1 for item in item_results if item.status == STATUS_NEEDS_REVIEW)
    quarantined_count = sum(1 for item in item_results if item.status == STATUS_QUARANTINED)
    failed_rule_count = sum(len(item.failed_rules) for item in item_results)

    if quarantined_count > 0:
        publish_status = PUBLISH_STATUS_BLOCKED
    elif needs_review_count > 0:
        publish_status = PUBLISH_STATUS_WARNING
    else:
        publish_status = PUBLISH_STATUS_PASS

    return MetadataValidationSummary(
        total_items=len(item_results),
        approved_count=approved_count,
        needs_review_count=needs_review_count,
        quarantined_count=quarantined_count,
        failed_rule_count=failed_rule_count,
        publish_status=publish_status,
    )


def _check_taxonomy_presence(target: MetadataValidationTarget) -> MetadataRuleResult:
    has_assignment = len(target.taxonomy_node_ids) > 0
    return MetadataRuleResult(
        rule_id=RULE_TAXONOMY_PRIMARY_ASSIGNMENT_MISSING,
        severity=SEVERITY_ERROR,
        passed=has_assignment,
        message=(
            "Primary taxonomy assignment present."
            if has_assignment
            else "KB article is missing a taxonomy assignment."
        ),
    )


def _check_taxonomy_known(
    target: MetadataValidationTarget,
    known_node_ids: frozenset[str],
) -> MetadataRuleResult:
    unknown_node_ids = tuple(node_id for node_id in target.taxonomy_node_ids if node_id not in known_node_ids)
    return MetadataRuleResult(
        rule_id=RULE_TAXONOMY_ASSIGNMENT_UNKNOWN_NODE,
        severity=SEVERITY_ERROR,
        passed=len(unknown_node_ids) == 0,
        message=(
            "All taxonomy assignments reference known nodes."
            if not unknown_node_ids
            else f"Unknown taxonomy node IDs: {', '.join(unknown_node_ids)}."
        ),
    )


def _check_taxonomy_active(
    target: MetadataValidationTarget,
    active_node_ids: frozenset[str],
) -> MetadataRuleResult:
    inactive_node_ids = tuple(
        node_id
        for node_id in target.taxonomy_node_ids
        if active_node_ids and node_id not in active_node_ids
    )
    return MetadataRuleResult(
        rule_id=RULE_TAXONOMY_ASSIGNMENT_INACTIVE_NODE,
        severity=SEVERITY_ERROR,
        passed=len(inactive_node_ids) == 0,
        message=(
            "All taxonomy assignments reference active nodes."
            if not inactive_node_ids
            else f"Inactive taxonomy node IDs: {', '.join(inactive_node_ids)}."
        ),
    )


def _check_authority_missing(target: MetadataValidationTarget) -> MetadataRuleResult:
    authority = _normalize_text(target.authority).lower()
    return MetadataRuleResult(
        rule_id=RULE_METADATA_AUTHORITY_MISSING,
        severity=SEVERITY_WARNING,
        passed=bool(authority),
        message=(
            "Authority is present."
            if authority
            else "Authority is missing and should be reviewed."
        ),
    )


def _check_authority_invalid(target: MetadataValidationTarget) -> MetadataRuleResult:
    authority = _normalize_text(target.authority).lower()
    invalid = bool(authority) and authority not in ALLOWED_AUTHORITIES
    return MetadataRuleResult(
        rule_id=RULE_METADATA_AUTHORITY_INVALID,
        severity=SEVERITY_ERROR,
        passed=not invalid,
        message=(
            "Authority value is valid."
            if not invalid
            else f"Authority '{target.authority}' is not in the allowed enum set."
        ),
    )


def _check_scope_missing(target: MetadataValidationTarget) -> MetadataRuleResult:
    scope = _normalize_text(target.scope).lower()
    return MetadataRuleResult(
        rule_id=RULE_METADATA_SCOPE_MISSING,
        severity=SEVERITY_WARNING,
        passed=bool(scope),
        message=(
            "Scope is present."
            if scope
            else "Scope is missing and should be reviewed."
        ),
    )


def _check_scope_invalid(target: MetadataValidationTarget) -> MetadataRuleResult:
    scope = _normalize_text(target.scope).lower()
    invalid = bool(scope) and scope not in ALLOWED_SCOPES
    return MetadataRuleResult(
        rule_id=RULE_METADATA_SCOPE_INVALID,
        severity=SEVERITY_ERROR,
        passed=not invalid,
        message=(
            "Scope value is valid."
            if not invalid
            else f"Scope '{target.scope}' is not in the allowed enum set."
        ),
    )


def _collect_label_values(target: MetadataValidationTarget) -> tuple[str, ...]:
    label_values = []
    question = _normalize_text(target.question)
    if question:
        label_values.append(question)
    category = _normalize_text(target.category)
    if category:
        label_values.append(category)
    label_values.extend(_normalize_text(tag) for tag in target.tags if _normalize_text(tag))
    return tuple(label_values)


def _check_label_empty(target: MetadataValidationTarget) -> MetadataRuleResult:
    question = _normalize_text(target.question)
    category = _normalize_text(target.category)
    if question and category:
        return MetadataRuleResult(
            rule_id=RULE_CONTENT_LABEL_EMPTY,
            severity=SEVERITY_WARNING,
            passed=True,
            message="Required label fields are populated.",
        )
    missing_fields = []
    if not question:
        missing_fields.append("question")
    if not category:
        missing_fields.append("category")
    return MetadataRuleResult(
        rule_id=RULE_CONTENT_LABEL_EMPTY,
        severity=SEVERITY_WARNING,
        passed=False,
        message=f"Empty required label fields: {', '.join(missing_fields)}.",
    )


def _check_label_placeholder(target: MetadataValidationTarget) -> MetadataRuleResult:
    label_values = _collect_label_values(target)
    placeholder_values = tuple(
        value for value in label_values if value.lower() in PLACEHOLDER_LABELS
    )
    return MetadataRuleResult(
        rule_id=RULE_CONTENT_LABEL_PLACEHOLDER,
        severity=SEVERITY_WARNING,
        passed=len(placeholder_values) == 0,
        message=(
            "No placeholder label text detected."
            if not placeholder_values
            else f"Placeholder label text detected: {', '.join(placeholder_values)}."
        ),
    )


def _check_label_too_short(target: MetadataValidationTarget) -> MetadataRuleResult:
    short_fields = []
    question = _normalize_text(target.question)
    if question and len(question) < 5:
        short_fields.append("question")
    category = _normalize_text(target.category)
    if category and len(category) < 3:
        short_fields.append("category")
    short_tags = tuple(tag for tag in target.tags if _normalize_text(tag) and len(_normalize_text(tag)) < 2)
    if short_tags:
        short_fields.append("tags")

    return MetadataRuleResult(
        rule_id=RULE_CONTENT_LABEL_TOO_SHORT,
        severity=SEVERITY_WARNING,
        passed=len(short_fields) == 0,
        message=(
            "Label lengths meet minimum thresholds."
            if not short_fields
            else f"Label text below minimum length for: {', '.join(short_fields)}."
        ),
    )
