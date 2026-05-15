"""
hub/retrieval/filter_policy.py

Central retrieval filter enforcement for Person 2 (Sprint 3).

This module is the single enforcement point for all safety/filter rules that
determine which KB articles are allowed to appear in resident-facing retrieval
results.  Both vector and lexical retrieval paths call into this module before
scoring, and a defense-in-depth post-fusion check uses the same logic to
verify that no excluded article slipped through.

Exclusion hierarchy (evaluated in order):
  1. Hard system rules  — enabled == 0  (disabled / unpublished)
  2. Validation status  — quarantined or rejected by the metadata review workflow
  3. Caller-supplied IDs — e.g. RLHF retry exclusions passed via exclude_source_ids

The module exposes two public helpers:
  • compute_excluded_article_ids(db, extra_exclude_ids)  → frozenset[int]
  • get_exclusion_log(db, excluded_ids)                   → list[dict]

All logging uses structured key=value pairs so Person 5's query-log columns
can consume them directly.
"""

from __future__ import annotations

import logging
from typing import Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy import func

from hub.db import schema

logger = logging.getLogger(__name__)

# ─── Exclusion reason codes (align with Person 5) ────────────────────────────
REASON_DISABLED = "disabled"
REASON_QUARANTINED = "quarantined"
REASON_REJECTED = "rejected"
REASON_CALLER_EXCLUDED = "caller_excluded"


# ─── Internal helpers ────────────────────────────────────────────────────────


def _get_disabled_article_ids(db: Session) -> set[int]:
    """Return IDs of all articles with enabled == 0."""
    rows = (
        db.query(schema.KBArticle.id)
        .filter(schema.KBArticle.enabled == 0)
        .all()
    )
    return {r[0] for r in rows}


def _get_validation_excluded_ids(db: Session) -> tuple[set[int], set[int]]:
    """Return (quarantined_ids, rejected_ids) based on latest validation status.

    Uses a subquery to find the most recent validation status row per article.
    Articles with no validation record are treated as implicitly approved
    (backwards-compatible with pre-Sprint-2 data).
    """
    # Subquery: max id per kb_item_id (most recent status row wins)
    latest_subq = (
        db.query(
            schema.KBItemValidationStatus.kb_item_id,
            func.max(schema.KBItemValidationStatus.id).label("max_id"),
        )
        .group_by(schema.KBItemValidationStatus.kb_item_id)
        .subquery()
    )

    # Join back to get the status value for each article's latest row
    rows = (
        db.query(
            schema.KBItemValidationStatus.kb_item_id,
            schema.KBItemValidationStatus.status,
        )
        .join(
            latest_subq,
            (schema.KBItemValidationStatus.kb_item_id == latest_subq.c.kb_item_id)
            & (schema.KBItemValidationStatus.id == latest_subq.c.max_id),
        )
        .all()
    )

    quarantined: set[int] = set()
    rejected: set[int] = set()
    for kb_item_id, status in rows:
        if status == "quarantined":
            quarantined.add(kb_item_id)
        elif status == "rejected":
            rejected.add(kb_item_id)

    return quarantined, rejected


# ─── Public API ──────────────────────────────────────────────────────────────


def compute_excluded_article_ids(
    db: Session,
    extra_exclude_ids: Optional[Set[int]] = None,
) -> frozenset[int]:
    """Return all article IDs that must be excluded from resident-facing retrieval.

    Exclusion order:
      1. Hard rule: disabled articles (enabled == 0)
      2. Validation: quarantined / rejected articles
      3. Caller-supplied: RLHF retry or ad-hoc exclusions

    Every call logs a structured summary so operators can inspect filter
    behavior from query logs.
    """
    disabled_ids = _get_disabled_article_ids(db)
    quarantined_ids, rejected_ids = _get_validation_excluded_ids(db)

    all_excluded: set[int] = set()
    all_excluded |= disabled_ids
    all_excluded |= quarantined_ids
    all_excluded |= rejected_ids
    if extra_exclude_ids:
        all_excluded |= extra_exclude_ids

    # Structured log — counts by reason
    logger.info(
        "[FilterPolicy] excluded_total=%d disabled=%d quarantined=%d "
        "rejected=%d caller=%d",
        len(all_excluded),
        len(disabled_ids),
        len(quarantined_ids),
        len(rejected_ids),
        len(extra_exclude_ids) if extra_exclude_ids else 0,
    )

    # Log individual article exclusions when the set is non-empty
    if quarantined_ids:
        logger.info(
            "[FilterPolicy] quarantined_ids=%s",
            sorted(quarantined_ids),
        )
    if rejected_ids:
        logger.info(
            "[FilterPolicy] rejected_ids=%s",
            sorted(rejected_ids),
        )

    return frozenset(all_excluded)


def get_exclusion_log(
    db: Session,
    excluded_ids: frozenset[int],
) -> list[dict]:
    """Return a list of {article_id, reason} entries for audit/logging.

    Useful for Person 5's query-log persistence and for debug inspection.
    """
    if not excluded_ids:
        return []

    disabled_ids = _get_disabled_article_ids(db)
    quarantined_ids, rejected_ids = _get_validation_excluded_ids(db)

    entries: list[dict] = []
    for aid in sorted(excluded_ids):
        if aid in disabled_ids:
            entries.append({"article_id": aid, "reason": REASON_DISABLED})
        elif aid in quarantined_ids:
            entries.append({"article_id": aid, "reason": REASON_QUARANTINED})
        elif aid in rejected_ids:
            entries.append({"article_id": aid, "reason": REASON_REJECTED})
        else:
            entries.append({"article_id": aid, "reason": REASON_CALLER_EXCLUDED})

    return entries


def filter_fused_results(
    fused_ids: list[int],
    excluded_ids: frozenset[int],
) -> list[int]:
    """Defense-in-depth: remove any excluded IDs from fused result list.

    This should be a no-op if pre-retrieval filtering is working correctly.
    Logs a warning if any articles are caught here (indicates a bug upstream).
    """
    if not excluded_ids:
        return fused_ids

    before_count = len(fused_ids)
    filtered = [aid for aid in fused_ids if aid not in excluded_ids]
    after_count = len(filtered)

    removed = before_count - after_count
    if removed > 0:
        caught_ids = [aid for aid in fused_ids if aid in excluded_ids]
        logger.warning(
            "[FilterPolicy] post_fusion_defense caught %d excluded article(s): %s "
            "(this indicates a pre-filter gap upstream)",
            removed,
            caught_ids,
        )
    else:
        logger.info(
            "[FilterPolicy] post_fusion_defense passed (no excluded articles in fused results)"
        )

    logger.info(
        "[FilterPolicy] fused_before=%d fused_after=%d removed=%d",
        before_count,
        after_count,
        removed,
    )

    return filtered
"""
hub/retrieval/filter_policy.py  — end of module
"""
