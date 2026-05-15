"""Slice 3 Story 4 — MVP metadata review workflow (admin API backing).

Builds the review queue from the same deterministic rules as publish (`validate_metadata`)
and applies human decisions to `kb_item_validation_status` + `kb_review_decisions`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from hub.db import schema
from hub.validation.metadata import (
    STATUS_APPROVED,
    STATUS_NEEDS_REVIEW,
    STATUS_QUARANTINED,
    load_taxonomy_reference,
    load_validation_targets,
    validate_metadata,
)

REVIEW_DECISION_APPROVED = "approved"
REVIEW_DECISION_REJECTED = "rejected"
REVIEW_DECISION_OVERRIDE = "override"

_ALLOWED_DECISIONS = frozenset(
    {REVIEW_DECISION_APPROVED, REVIEW_DECISION_REJECTED, REVIEW_DECISION_OVERRIDE}
)


def get_system_kb_version(db: Session) -> int:
    row = db.query(schema.SystemVersion).first()
    return int(row.kb_version or 0) if row else 0


def latest_validation_status_row(
    db: Session, kb_item_id: int
) -> schema.KBItemValidationStatus | None:
    return (
        db.query(schema.KBItemValidationStatus)
        .filter(schema.KBItemValidationStatus.kb_item_id == kb_item_id)
        .order_by(schema.KBItemValidationStatus.id.desc())
        .first()
    )


def _rule_result_to_dict(r) -> dict[str, Any]:
    return {
        "rule_id": r.rule_id,
        "severity": r.severity,
        "passed": r.passed,
        "message": r.message,
    }


def build_review_queue(db: Session) -> tuple[list[dict[str, Any]], int]:
    """Items that need operator attention: live quarantined/needs_review, excluding
    items whose latest persisted status is already `approved` (includes override).
    """
    kb_version = get_system_kb_version(db)
    targets = load_validation_targets(db)
    known_ids, active_ids = load_taxonomy_reference(db)
    run = validate_metadata(targets, known_ids, active_ids)

    out: list[dict[str, Any]] = []
    for item in run.items:
        if item.status not in (STATUS_QUARANTINED, STATUS_NEEDS_REVIEW):
            continue
        latest = latest_validation_status_row(db, item.article_id)
        if latest and latest.status == STATUS_APPROVED:
            continue
        failed = [rr for rr in item.rule_results if not rr.passed]
        out.append(
            {
                "kb_item_id": item.article_id,
                "live_status": item.status,
                "kb_version": kb_version,
                "latest_db_status": latest.status if latest else None,
                "failed_rules": [_rule_result_to_dict(rr) for rr in failed],
            }
        )
    # Stable ordering for console
    out.sort(key=lambda x: x["kb_item_id"])
    return out, kb_version


def build_article_validation_detail(db: Session, kb_item_id: int) -> dict[str, Any]:
    art = db.query(schema.KBArticle).filter(schema.KBArticle.id == kb_item_id).first()
    if not art:
        return {}

    kb_version = get_system_kb_version(db)
    targets = load_validation_targets(db)
    known_ids, active_ids = load_taxonomy_reference(db)
    run = validate_metadata(targets, known_ids, active_ids)
    live_item = next((i for i in run.items if i.article_id == kb_item_id), None)
    if not live_item:
        live_status = STATUS_APPROVED
        live_rules = []
    else:
        live_status = live_item.status
        live_rules = [_rule_result_to_dict(r) for r in live_item.rule_results]

    vrows = (
        db.query(schema.KBValidationResult)
        .filter(schema.KBValidationResult.kb_item_id == kb_item_id)
        .order_by(schema.KBValidationResult.id.asc())
        .all()
    )
    persisted = [
        {
            "id": r.id,
            "kb_item_id": r.kb_item_id,
            "publish_attempt_id": r.publish_attempt_id,
            "kb_version": r.kb_version,
            "rule_id": r.rule_id,
            "severity": r.severity,
            "message": r.message,
            "passed": bool(r.passed),
            "checked_at": r.checked_at.isoformat() if r.checked_at else None,
        }
        for r in vrows
    ]

    drows = (
        db.query(schema.KBReviewDecision)
        .filter(schema.KBReviewDecision.kb_item_id == kb_item_id)
        .order_by(schema.KBReviewDecision.id.asc())
        .all()
    )
    decisions = [
        {
            "id": r.id,
            "kb_item_id": r.kb_item_id,
            "publish_attempt_id": r.publish_attempt_id,
            "kb_version": r.kb_version,
            "reviewer_id": r.reviewer_id,
            "decision": r.decision,
            "reason_code": r.reason_code,
            "notes": r.notes,
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        }
        for r in drows
    ]

    return {
        "kb_item_id": kb_item_id,
        "kb_version": kb_version,
        "article": {
            "id": art.id,
            "question": art.question,
            "answer": art.answer,
            "category": art.category,
            "tags": art.tags,
            "enabled": bool(art.enabled),
            "authority": art.authority,
            "scope": art.scope,
            "status": art.status,
        },
        "live_status": live_status,
        "live_rule_results": live_rules,
        "persisted_validation_results": persisted,
        "review_decisions": decisions,
    }


def apply_metadata_review(
    db: Session,
    *,
    reviewer: schema.User,
    kb_item_id: int,
    kb_version: int,
    decision: str,
    reason_code: str | None,
    notes: str | None,
    publish_attempt_id: int | None,
) -> tuple[str, schema.KBItemValidationStatus, schema.KBReviewDecision]:
    if decision not in _ALLOWED_DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")
    if decision == REVIEW_DECISION_OVERRIDE:
        if not (reason_code and reason_code.strip()):
            raise ValueError("reason_code is required for override decisions")

    art = db.query(schema.KBArticle).filter(schema.KBArticle.id == kb_item_id).first()
    if not art:
        raise ValueError("KB article not found")

    if decision in (REVIEW_DECISION_APPROVED, REVIEW_DECISION_OVERRIDE):
        new_validation_status = STATUS_APPROVED
    else:
        new_validation_status = "rejected"

    reviewer_id = reviewer.username or str(reviewer.user_id)

    status_row = schema.KBItemValidationStatus(
        kb_item_id=kb_item_id,
        publish_attempt_id=publish_attempt_id,
        kb_version=kb_version,
        status=new_validation_status,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(status_row)

    decision_row = schema.KBReviewDecision(
        kb_item_id=kb_item_id,
        publish_attempt_id=publish_attempt_id,
        kb_version=kb_version,
        reviewer_id=reviewer_id,
        decision=decision,
        reason_code=(reason_code.strip() if reason_code else None),
        notes=notes,
        decided_at=datetime.utcnow(),
    )
    db.add(decision_row)

    return new_validation_status, status_row, decision_row
