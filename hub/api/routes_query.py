import time
import asyncio
import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models
from hub.retrieval import search, translator
from hub.retrieval import formatter
from hub.retrieval.pipeline import QueryPipeline

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store: maps session_id → list of {user, assistant} dicts
session_history = {}


def _json_result_field(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _retrieval_score_for_log(result: dict) -> float:
    confidence_raw = result.get("confidence_raw")
    if confidence_raw is not None:
        return float(confidence_raw)
    return float(result.get("confidence") or 0.0)


# Pipeline: Kiosk sends user text -> Hub receives -> if not English translate to EN (NLLB)
# -> semantic search -> top result -> LLM format -> if not English translate answer back (NLLB)
# -> return to kiosk -> kiosk TTS.


@router.post("/query", response_model=api_models.QueryResponse)
async def submit_query(query: api_models.QueryRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    try:
        user_language = query.language or "en"
        raw_text = (query.transcript_english or query.transcript_original).strip()
        logger.info(f"[Query] Incoming: lang={user_language} raw='{raw_text[:80]}' is_retry={query.is_retry} exclude_source_ids={query.exclude_source_ids}")

        # Non-English: translate input to EN for search; after retrieval/LLM, translate answer back to user language (below)
        if user_language != "en":
            try:
                text = translator.translate(raw_text, user_language, "en")
                logger.info(f"[Query] Translated ({user_language}->en): '{text[:80]}'")
            except Exception as e:
                logger.error(f"[Query] Inbound translation failed: {e}")
                text = raw_text
        else:
            text = raw_text

        # Apply raw-language normalization as a fallback enrichment for non-English
        if user_language != "en":
            try:
                from hub.retrieval.normalizer import normalize_query
                raw_norm = normalize_query(raw_text, user_language)
                if raw_norm and raw_norm not in text:
                    text = f"{text} {raw_norm}".strip()
            except Exception:
                pass

        # Determine query language for the pipeline (if translation failed, query
        # may still be in the original language).
        query_lang = "en"
        if user_language != "en" and text == raw_text:
            query_lang = user_language

        # ── Canonical pipeline ────────────────────────────────────────────────
        # normalize → intent → retrieve → clarification_gate → rewrite → retrieve_retry
        t1 = time.time()
        pipeline = QueryPipeline()
        pipeline_result = pipeline.run(
            db,
            text,
            query.is_retry,
            query.selected_category,
            query.exclude_source_ids,
            query_language=query_lang,
        )
        logger.info(
            f"[Query] Pipeline completed in {(time.time() - t1) * 1000:.0f}ms "
            f"stages={pipeline_result.stage_log}"
        )

        try:
            t1 = time.time()
            query_lang = "en"
            if user_language != "en" and text == raw_text:
                query_lang = user_language
            result = search.retrieve(
                db,
                text,
                query.is_retry,
                query.selected_category,
                query.selected_taxonomy_node_id,
                query.exclude_source_ids,
                query_language=query_lang,
            )
            logger.info(f"[Query] Retrieval took {(time.time() - t1) * 1000:.0f}ms")
        except Exception as e:
            logger.error(f"[Query] Retrieval error: {e}")
            result = {
                "answer_text": "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
                "answer_type": "NO_MATCH",
                "confidence": 0.0,
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": "unclear",
                "intent_confidence": 0.0,
            }

        # Track rewrite state for logging
        rewritten_text = text
        rewrite_happened = False
        follow_up_prompt = result.get("follow_up_prompt")
        follow_up_intent = result.get("follow_up_intent")

        # Sync normalized text back so logging below references pipeline output.
        text = pipeline_result.normalized_text or text

        answer_type = result["answer_type"]
        confidence = result["confidence"]

        # ── Clarification pause: early-return ─────────────────────────────
        # When the pipeline is paused for clarification, build a structured
        # ClarificationContext with all resume fields and return immediately.
        # This skips LLM formatting and outbound translation (wasted work
        # for a response that just shows category chips on the kiosk).
        if pipeline_result.pipeline_status == "paused":
            # Build typed taxonomy-backed chip options from the raw dicts
            # returned by search.py's _deterministic_clarification_node_ids().
            raw_opts = result.get("clarification_options") or []
            taxonomy_options = None
            if raw_opts:
                taxonomy_options = [
                    api_models.TaxonomyOption(id=opt["id"], label=opt["label"])
                    for opt in raw_opts
                    if isinstance(opt, dict) and opt.get("id") and opt.get("label")
                ]
                if not taxonomy_options:
                    taxonomy_options = None

            clarification_ctx = api_models.ClarificationContext(
                original_query=raw_text,
                normalized_text=pipeline_result.normalized_text,
                detected_intent=pipeline_result.intent,
                intent_confidence=pipeline_result.intent_confidence,
                suggested_categories=result.get("categories") or [],
                clarification_options=taxonomy_options,
                kb_version=query.kb_version,
                session_id=query.session_id,
                pipeline_status="paused",
            )

            # HOOK: Person 2 — log clarification pause state
            # clarification_ctx contains all fields needed for the pause audit log.
            logger.info(
                f"[Query] PAUSED for clarification | intent={pipeline_result.intent} "
                f"confidence={pipeline_result.intent_confidence:.4f} "
                f"categories={clarification_ctx.suggested_categories} "
                f"options={len(taxonomy_options) if taxonomy_options else 0} "
                f"session={query.session_id}"
            )

            # Still write query log so operators can join on it
            pause_log_id = None
            try:
                import time as _time
                _clarification_options_shown = None
                try:
                    opts = result.get("clarification_options") or []
                    if opts:
                        _clarification_options_shown = json.dumps(opts, ensure_ascii=False)
                except Exception:
                    pass
                log_entry = schema.QueryLog(
                    kiosk_id=query.kiosk_id or "",
                    session_id=query.session_id,
                    transcript_original=query.transcript_original,
                    transcript_english=text,
                    raw_transcript=raw_text,
                    normalized_transcript=pipeline_result.normalized_text,
                    language=user_language,
                    kb_version=query.kb_version,
                    retrieval_score=_retrieval_score_for_log(result),
                    answer_type=answer_type,
                    source_id=result.get("source_id"),
                    rewrite_attempted=False,
                    rewritten_query=None,
                    latency_ms=round((time.time() - start_time) * 1000, 2),
                    clarification_triggered=pipeline_result.clarification_triggered,
                    clarification_trigger_reason=pipeline_result.clarification_trigger_reason,
                    clarification_options_shown=_clarification_options_shown,
                    pipeline_stage_log=json.dumps(pipeline_result.stage_log, ensure_ascii=False),
                    intent_label=pipeline_result.intent,
                    intent_confidence=pipeline_result.intent_confidence,
                    lexical_top_k_ids=_json_result_field(result.get("lexical_top_k_ids")),
                    lexical_top_k_scores=_json_result_field(result.get("lexical_top_k_scores")),
                    lexical_top_k_ranks=_json_result_field(result.get("lexical_top_k_ranks")),
                    lexical_latency_ms=result.get("lexical_latency_ms"),
                    vector_top_k_ids=_json_result_field(result.get("vector_top_k_ids")),
                    vector_top_k_scores=_json_result_field(result.get("vector_top_k_scores")),
                    vector_top_k_ranks=_json_result_field(result.get("vector_top_k_ranks")),
                    fusion_strategy=result.get("fusion_strategy"),
                    fusion_top_k_ids=_json_result_field(result.get("fusion_top_k_ids")),
                    fusion_top_k_scores=_json_result_field(result.get("fusion_top_k_scores")),
                    fusion_top_k_ranks=_json_result_field(result.get("fusion_top_k_ranks")),
                    created_at=int(_time.time()),
                )
                db.add(log_entry)
                db.commit()
                pause_log_id = log_entry.id
            except Exception as e:
                logger.exception("[Query] DB log/commit failed for paused query")
                db.rollback()

            return api_models.QueryResponse(
                answer_text_en=result.get("answer_text") or "Could you clarify what you need help with?",
                answer_text_localized=None,
                answer_type=answer_type,
                confidence=float(confidence),
                kb_version=query.kb_version,
                source_id=result.get("source_id"),
                clarification_categories=result.get("categories"),
                clarification_options=taxonomy_options,
                query_log_id=pause_log_id,
                clarification_context=clarification_ctx,
            )

        if answer_type == "DIRECT_MATCH" and result.get("article_data"):
            history_str = ""
            # Do not use session history if this is a retry, as the LLM will see the disliked answer
            # and may lazily hallucinate and repeat the exact same response instead of using the new KB article.
            if query.session_id and query.session_id in session_history and not query.is_retry:
                history_str = json.dumps(session_history[query.session_id][-3:], ensure_ascii=False)
            article_json = json.dumps(result["article_data"], ensure_ascii=False)
            try:
                answer_text = await asyncio.to_thread(
                    formatter.format_response,
                    article_json,
                    text,
                    history_str,
                    include_intro=False,
                )
            except Exception as e:
                logger.error(f"[Query] Formatter error: {e}")
                answer_text = result["article_data"].get("answer", result["answer_text"])
        else:
            answer_text = result.get("answer_text") or ""

        # For compound queries, emit a single assistant message:
        # primary answer + inline yes/no follow-up question.
        if (
            answer_type == "DIRECT_MATCH"
            and not query.is_retry
            and follow_up_prompt
            and answer_text
        ):
            contextual_follow_up = follow_up_prompt
            try:
                contextual_follow_up = await asyncio.to_thread(
                    formatter.generate_follow_up_prompt,
                    text,
                    follow_up_intent or "",
                    follow_up_prompt,
                )
            except Exception as e:
                logger.warning(f"[Query] Follow-up prompt generation failed: {e}")
            answer_text = f"{answer_text.strip()}\n\n{contextual_follow_up.strip()}"

        if not (answer_text and answer_text.strip()):
            answer_text = "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help."

        latency = (time.time() - start_time) * 1000
        logger.info(
            f"[Query] {answer_type} in {latency:.0f}ms | conf={confidence:.2f} | lang={user_language} "
            f"| is_compound={bool(result.get('is_compound'))} | primary={result.get('intent')} | secondary={follow_up_intent} "
            f"| follow_up_prompt_emitted={bool(follow_up_prompt)}"
        )

        # Translate answer back to user's language
        answer_text_localized = None
        if user_language != "en" and answer_text:
            try:
                translated = translator.translate(answer_text, "en", user_language)
                # If translation returns the same text, treat it as a no-op so the
                # client does not mistake English for a localized answer.
                if translated and translated.strip() != answer_text.strip():
                    answer_text_localized = translated
                    logger.info(f"[Query] Translated to {user_language}: '{answer_text_localized[:80]}...'")
                else:
                    answer_text_localized = None
                    logger.info(f"[Query] Translation to {user_language} produced no change; using English answer.")
            except Exception as e:
                logger.error(f"[Query] Translation failed: {e}")

        query_log_id = None
        try:
            import time as _time
            inferred_ids = result.get("inferred_taxonomy_node_ids")
            inferred_ids_json = None
            try:
                if isinstance(inferred_ids, list):
                    inferred_ids_json = json.dumps(inferred_ids, ensure_ascii=False)
            except Exception:
                inferred_ids_json = None
            log_entry = schema.QueryLog(
                kiosk_id=query.kiosk_id or "",
                session_id=query.session_id,
                rlhf_top_source_id=result.get("rlhf_top_source_id"),
                rlhf_top_score=result.get("rlhf_top_score"),
                transcript_original=query.transcript_original,
                transcript_english=text,
                raw_transcript=raw_text,
                normalized_transcript=text,
                language=user_language,
                kb_version=query.kb_version,
                retrieval_score=_retrieval_score_for_log(result),
                answer_type=answer_type,
                source_id=result.get("source_id"),
                rewrite_attempted=True if rewrite_happened else False,
                rewritten_query=rewritten_text if rewrite_happened else None,
                latency_ms=round(latency, 2),
                ui_selection_source=result.get("ui_selection_source"),
                ui_selected_taxonomy_node_id=result.get("ui_selected_taxonomy_node_id"),
                ui_selected_taxonomy_node_label=result.get("ui_selected_taxonomy_node_label"),
                inferred_taxonomy_node_ids=inferred_ids_json,
                widening_step=result.get("widening_step"),
                widening_reason=result.get("widening_reason"),
                clarification_triggered=pipeline_result.clarification_triggered,
                clarification_trigger_reason=pipeline_result.clarification_trigger_reason,
                clarification_options_shown=None,  # not triggered; no options were shown
                pipeline_stage_log=json.dumps(pipeline_result.stage_log, ensure_ascii=False),
                intent_label=pipeline_result.intent,
                intent_confidence=pipeline_result.intent_confidence,
                lexical_top_k_ids=_json_result_field(result.get("lexical_top_k_ids")),
                lexical_top_k_scores=_json_result_field(result.get("lexical_top_k_scores")),
                lexical_top_k_ranks=_json_result_field(result.get("lexical_top_k_ranks")),
                lexical_latency_ms=result.get("lexical_latency_ms"),
                vector_top_k_ids=_json_result_field(result.get("vector_top_k_ids")),
                vector_top_k_scores=_json_result_field(result.get("vector_top_k_scores")),
                vector_top_k_ranks=_json_result_field(result.get("vector_top_k_ranks")),
                fusion_strategy=result.get("fusion_strategy"),
                fusion_top_k_ids=_json_result_field(result.get("fusion_top_k_ids")),
                fusion_top_k_scores=_json_result_field(result.get("fusion_top_k_scores")),
                fusion_top_k_ranks=_json_result_field(result.get("fusion_top_k_ranks")),
                created_at=int(_time.time()),
            )
            db.add(log_entry)
            db.commit()
            query_log_id = log_entry.id

            # ── Clarification resolution: persist chip selection (Story 5) ──
            # Write only when this request is a retry that carried a chip selection
            # so that operators can review what residents chose to resolve ambiguity.
            if query.is_retry and (query.selected_taxonomy_node_id or query.selected_category):
                try:
                    selected_id = query.selected_taxonomy_node_id or query.selected_category
                    selected_label = (
                        result.get("ui_selected_taxonomy_node_label")
                        or query.selected_category
                    )
                    resolution = schema.ClarificationResolution(
                        session_id=query.session_id or "",
                        raw_transcript=query.transcript_original,
                        resolved_intent=result.get("intent") or "unclear",
                        language=user_language,
                        selected_option_id=selected_id,
                        selected_option_label=selected_label,
                        query_log_id=query_log_id,
                    )
                    db.add(resolution)
                    db.commit()
                    logger.info(
                        f"[Clarification] Resolution persisted | "
                        f"session={query.session_id} option_id={selected_id} "
                        f"label={selected_label} intent={result.get('intent')} "
                        f"query_log_id={query_log_id}"
                    )
                except Exception as cr_err:
                    logger.warning(f"[Clarification] Resolution persist failed: {cr_err}")
                    db.rollback()

            # ── FAQ Tracker: upsert by source_id (KB article) ──────────────
            try:
                matched_source_id = result.get("source_id")
                if matched_source_id and answer_type == "DIRECT_MATCH":
                    now_ts = int(_time.time())
                    q_text = raw_text.strip()

                    existing = db.query(schema.FAQTracker).filter(
                        schema.FAQTracker.source_id == matched_source_id
                    ).first()

                    if existing:
                        existing.count += 1
                        existing.last_asked_at = now_ts
                        existing.kiosk_id = query.kiosk_id or existing.kiosk_id
                        existing.language = user_language
                        existing.question_display = q_text
                        existing.question_normalized = q_text.lower()
                    else:
                        # Fetch the KB article question/answer for display
                        kb_article = db.query(schema.KBArticle).filter(
                            schema.KBArticle.id == matched_source_id
                        ).first()
                        source_q = kb_article.question if kb_article else q_text
                        source_a = kb_article.answer[:200] if kb_article and kb_article.answer else ""

                        faq_entry = schema.FAQTracker(
                            source_id=matched_source_id,
                            source_question=source_q,
                            source_answer=source_a,
                            question_normalized=q_text.lower(),
                            question_display=q_text,
                            language=user_language,
                            count=1,
                            first_asked_at=now_ts,
                            last_asked_at=now_ts,
                            kiosk_id=query.kiosk_id or "",
                            answer_type=answer_type,
                        )
                        db.add(faq_entry)
                    db.commit()
            except Exception as faq_err:
                logger.warning(f"[FAQ Tracker] Upsert failed: {faq_err}")
                db.rollback()

        except Exception as e:
            logger.exception("[Query] DB log/commit failed")
            db.rollback()

        if query.session_id:
            if query.session_id not in session_history:
                session_history[query.session_id] = []
            session_history[query.session_id].append({"user": text, "assistant": answer_text})

        return api_models.QueryResponse(
            answer_text_en=answer_text,
            answer_text_localized=answer_text_localized,
            answer_type=answer_type,
            confidence=float(confidence),
            kb_version=query.kb_version,
            source_id=result.get("source_id"),
            clarification_categories=result.get("categories"),
            clarification_options=result.get("clarification_options"),
            query_log_id=query_log_id,
            rlhf_top_source_id=result.get("rlhf_top_source_id"),
            rlhf_top_score=result.get("rlhf_top_score"),
            follow_up_prompt=follow_up_prompt,
            follow_up_intent=follow_up_intent,
        )

    except Exception:
        logger.exception("Query failed")
        return api_models.QueryResponse(
            answer_text_en="I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
            answer_text_localized=None,
            answer_type="NO_MATCH",
            confidence=0.0,
            kb_version=getattr(query, "kb_version", 1),
            source_id=None,
            clarification_categories=None,
            follow_up_prompt=None,
            follow_up_intent=None,
        )


@router.delete("/query/session/{session_id}")
async def end_session(session_id: str):
    if session_id in session_history:
        del session_history[session_id]
        logger.info(f"Session {session_id} deleted.")
        return {"status": "success", "message": "Session ended."}
    return {"status": "ok", "message": "Session not found."}


@router.get("/faq/suggestions", response_model=list[api_models.FaqSuggestionItem])
async def get_faq_suggestions(limit: int = 5, db: Session = Depends(get_db)):
    """Return the top N most-asked questions for kiosk suggestion chips."""
    rows = (
        db.query(schema.FAQTracker)
        .filter(schema.FAQTracker.source_question.isnot(None))
        .order_by(schema.FAQTracker.count.desc())
        .limit(limit)
        .all()
    )
    return [
        api_models.FaqSuggestionItem(
            source_id=r.source_id,
            question=r.source_question,
            count=r.count,
        )
        for r in rows
    ]


@router.post("/feedback")
async def submit_feedback(feedback: api_models.FeedbackRequest, db: Session = Depends(get_db)):
    """Record kiosk feedback for RLHF-style ranking. Fire-and-forget on the kiosk side."""
    try:
        entry = schema.FeedbackLog(
            session_id=feedback.session_id,
            query_log_id=feedback.query_log_id,
            source_id=feedback.source_id,
            label=feedback.label,
            language=feedback.language,
            kiosk_id=feedback.kiosk_id,
            center_id=feedback.center_id,
        )
        db.add(entry)
        db.commit()
        return {"status": "ok"}
    except Exception:
        logger.exception("[Feedback] DB log/commit failed")
        db.rollback()
        # Surface an error to callers; kiosk treats this as non-blocking.
        raise HTTPException(status_code=500, detail="Failed to record feedback")
