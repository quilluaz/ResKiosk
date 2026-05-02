"""
hub/retrieval/pipeline.py

Canonical query pipeline for the ResKiosk hub.

Enforced stage order:
  1. normalize
  2. intent classification
  3. retrieve (first pass)
  4. clarification gate — STOP here if NEEDS_CLARIFICATION
  5. rewrite (only if clarification not needed)
  6. retrieve (second pass, only if rewrite produced a different query)

The pipeline returns a PipelineResult. The route handler is responsible for
translation (pre/post pipeline), LLM response formatting, logging, and
session history — none of that belongs here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from hub.retrieval.normalizer import normalize_query
from hub.retrieval import search
from hub.retrieval import rewriter as query_rewriter

logger = logging.getLogger(__name__)

# Sentinel used by tests to verify stage log entries.
STAGE_NORMALIZE = "normalize"
STAGE_INTENT = "intent"
STAGE_RETRIEVE = "retrieve"
STAGE_CLARIFICATION_GATE = "clarification_gate"
STAGE_REWRITE = "rewrite"
STAGE_RETRIEVE_RETRY = "retrieve_retry"


@dataclass
class PipelineResult:
    """
    Carries all outputs produced by the pipeline run.

    stage_log is an ordered list of stage name constants that were executed.
    Consumers (and tests) can inspect this list to assert that stages ran in
    the correct order and that prohibited stages were skipped.
    """

    # The normalized English query text sent to the first retrieval pass.
    normalized_text: str = ""

    # Intent classification results.
    intent: str = "unclear"
    intent_confidence: float = 0.0

    # The retrieval result dict (from search.retrieve).
    retrieve_result: dict = field(default_factory=dict)

    # Rewrite state.
    rewrite_happened: bool = False
    rewritten_text: Optional[str] = None

    # Ordered record of pipeline stages that executed.
    stage_log: List[str] = field(default_factory=list)


class QueryPipeline:
    """
    Orchestrates the canonical hub query processing pipeline.

    Usage:
        pipeline = QueryPipeline()
        result = pipeline.run(db, text_en, is_retry, selected_category, exclude_source_ids, query_language)
    """

    def run(
        self,
        db: Session,
        text_en: str,
        is_retry: bool,
        selected_category: Optional[str] = None,
        exclude_source_ids: Optional[List[int]] = None,
        query_language: str = "en",
    ) -> PipelineResult:
        """
        Run the canonical pipeline and return a PipelineResult.

        Stage order is strictly:
          normalize → intent → retrieve → clarification_gate → rewrite → retrieve_retry
        """
        result = PipelineResult()

        # ── Stage 1: Normalize ────────────────────────────────────────────────
        result.stage_log.append(STAGE_NORMALIZE)
        normalized = normalize_query(text_en, query_language)
        result.normalized_text = normalized
        logger.debug(f"[Pipeline] {STAGE_NORMALIZE}: '{normalized[:80]}'")

        # ── Stage 2: Intent ───────────────────────────────────────────────────
        # Intent classification is surfaced here so it can be logged and tested
        # independently of the retrieval internals.  search.retrieve() will
        # also run intent internally (it has its own classifier reference),
        # which is intentional — we do not strip intent from retrieve() this
        # increment to keep the scope bounded.
        result.stage_log.append(STAGE_INTENT)
        intent, intent_confidence = self._classify_intent(normalized)
        result.intent = intent
        result.intent_confidence = intent_confidence
        logger.debug(
            f"[Pipeline] {STAGE_INTENT}: intent={intent} conf={intent_confidence:.4f}"
        )

        # ── Stage 3: Retrieve (first pass) ───────────────────────────────────
        result.stage_log.append(STAGE_RETRIEVE)
        try:
            retrieve_result = search.retrieve(
                db,
                normalized,
                is_retry,
                selected_category,
                exclude_source_ids,
                query_language=query_language,
            )
        except Exception as e:
            logger.error(f"[Pipeline] Retrieval error: {e}")
            retrieve_result = _fallback_no_match(intent, intent_confidence)
        result.retrieve_result = retrieve_result
        logger.debug(
            f"[Pipeline] {STAGE_RETRIEVE}: answer_type={retrieve_result.get('answer_type')} "
            f"confidence={retrieve_result.get('confidence', 0.0):.4f}"
        )

        # ── Stage 4: Clarification gate ───────────────────────────────────────
        # If retrieval determined clarification is needed, we stop here.
        # Rewrite MUST NOT run, and no second retrieval pass occurs.
        result.stage_log.append(STAGE_CLARIFICATION_GATE)
        if retrieve_result.get("answer_type") == "NEEDS_CLARIFICATION":
            logger.debug(
                f"[Pipeline] {STAGE_CLARIFICATION_GATE}: clarification required — "
                "stopping pipeline before rewrite."
            )
            return result

        # ── Stage 5: Rewrite (only if clarification not needed) ──────────────
        result.stage_log.append(STAGE_REWRITE)
        candidate = query_rewriter.maybe_rewrite(
            normalized,
            retrieve_result.get("intent", intent),
            retrieve_result.get("confidence", 0.0),
        )
        rewrite_happened = candidate != normalized
        result.rewritten_text = candidate if rewrite_happened else None
        result.rewrite_happened = rewrite_happened
        logger.debug(
            f"[Pipeline] {STAGE_REWRITE}: rewrite_happened={rewrite_happened} "
            f"candidate='{candidate[:60]}'"
        )

        # ── Stage 6: Retrieve (retry after rewrite) ───────────────────────────
        if rewrite_happened:
            result.stage_log.append(STAGE_RETRIEVE_RETRY)
            try:
                retry_result = search.retrieve(
                    db,
                    candidate,
                    False,
                    None,
                    exclude_source_ids,
                    query_language=query_language,
                )
                logger.debug(
                    f"[Pipeline] {STAGE_RETRIEVE_RETRY}: "
                    f"'{normalized[:40]}' → '{candidate[:40]}' "
                    f"→ {retry_result.get('answer_type')}"
                )
                result.retrieve_result = retry_result
            except Exception as e:
                logger.warning(f"[Pipeline] Rewrite retry failed: {e}")
                # Keep the original retrieve_result on failure.

        return result

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _classify_intent(normalized_query: str):
        """
        Attempt intent classification using the search module's singleton
        classifier. Returns (intent, confidence). Degrades gracefully when
        no classifier is loaded.
        """
        classifier = search._intent_classifier  # type: ignore[attr-defined]
        if classifier is None:
            return "unclear", 0.0
        try:
            if hasattr(classifier, "classify_top2"):
                intent, conf, _, _ = classifier.classify_top2(normalized_query)
            else:
                intent, conf = classifier.classify(normalized_query)
            return intent, float(conf)
        except Exception as e:
            logger.warning(f"[Pipeline] Intent classification failed: {e}")
            return "unclear", 0.0


def _fallback_no_match(intent: str, intent_confidence: float) -> dict:
    return {
        "answer_text": (
            "I am here to answer questions about registration, food, medical help, "
            "sleeping areas, transportation, safety, and other services in this shelter. "
            "Please ask about one of these topics or see a volunteer for more help."
        ),
        "answer_type": "NO_MATCH",
        "confidence": 0.0,
        "source_id": None,
        "categories": None,
        "article_data": None,
        "intent": intent,
        "intent_confidence": intent_confidence,
    }
