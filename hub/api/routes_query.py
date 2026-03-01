import time
import asyncio
import logging
import json as _json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models
from hub.retrieval import search, formatter, translator
from hub.retrieval import rewriter as query_rewriter
from hub.retrieval.normalizer import normalize_query

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store: maps session_id → list of {user, assistant} dicts
# session_history = {} (Using Database persistence now)


# Pipeline: Kiosk sends user text -> Hub receives -> if not English translate to EN (NLLB)
# -> semantic search -> top result -> LLM format -> if not English translate answer back (NLLB)
# -> return to kiosk -> kiosk TTS.


@router.post("/query", response_model=api_models.QueryResponse)
async def submit_query(query: api_models.QueryRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    try:
        user_language = query.language or "en"
        raw_text = (query.transcript_english or query.transcript_original).strip()
        logger.info(f"[Query] Incoming: lang={user_language} session={query.session_id} raw='{raw_text[:80]}' is_retry={query.is_retry}")


        # Non-English: translate input to EN for search; after retrieval/LLM, translate answer back to user language (below)
        if user_language != "en":
            try:
                text = await asyncio.to_thread(translator.translate, raw_text, user_language, "en")
                logger.info(f"[Query] Translated ({user_language}->en): '{text[:80]}'")
            except Exception as e:
                logger.error(f"[Query] Inbound translation failed: {e}")
                text = raw_text
        else:
            text = raw_text

        history = []
        if query.session_id:
            # Load history from DB
            try:
                history_rows = db.query(schema.SessionHistory).filter(schema.SessionHistory.session_id == query.session_id).order_by(schema.SessionHistory.id.asc()).all()
                history = [{"user": r.user_msg, "assistant": r.assistant_msg} for r in history_rows]
                logger.info(f"[Query] Session: {query.session_id} | Hist: {len(history)} turns from DB")
            except Exception as e:
                logger.warning(f"[Query] Failed to load history: {e}")

        # Contextual Resolve: If follow-up question (e.g. "When?"), resolve using session history
        ctx_rewritten = False
        if query.session_id and history and not query.is_retry:
            try:
                resolved_text = await asyncio.to_thread(query_rewriter.rewrite_contextual, text, history)
                if resolved_text != text:
                    logger.info(f"[Query] Contextual RESOLVED: '{text}' -> '{resolved_text}'")
                    text = resolved_text
                    ctx_rewritten = True
                else:
                    logger.info(f"[Query] Contextual NO CHANGE for: '{text}'")
            except Exception as e:
                logger.warning(f"[Query] Contextual rewrite failed: {e}")

        # Apply raw-language normalization as a fallback enrichment for non-English
        if user_language != "en":
            try:
                raw_norm = normalize_query(raw_text, user_language)
                if raw_norm and raw_norm not in text:
                    text = f"{text} {raw_norm}".strip()
            except Exception:
                pass

        normalize_query(text)  # kept for side-effects / logging

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
        rewrite_happened = ctx_rewritten

        # Query rewrite on low-confidence results
        if result["answer_type"] in ("NO_MATCH", "NEEDS_CLARIFICATION"):
            candidate = query_rewriter.maybe_rewrite(
                text,
                result.get("intent", "unclear"),
                result["confidence"],
            )
            if candidate != text:
                try:
                    retry_result = search.retrieve(
                        db,
                        candidate,
                        False,
                        None,
                        query.exclude_source_ids,
                        query_language=query_lang,
                    )
                    logger.info(f"[Query] Noise rewrite retry: '{text[:40]}' -> '{candidate[:40]}' -> {retry_result['answer_type']}")
                    result = retry_result
                    rewritten_text = candidate
                    rewrite_happened = True
                except Exception as e:
                    logger.warning(f"[Query] Rewrite retry failed: {e}")

        answer_type = result["answer_type"]
        confidence = result["confidence"]

        if answer_type == "DIRECT_MATCH" and result.get("article_data"):
            history_str = ""
            # Do not use session history if this is a retry, as the LLM will see the disliked answer
            # and may lazily hallucinate and repeat the exact same response instead of using the new KB article.
            if query.session_id and history and not query.is_retry:
                history_str = _json.dumps(history[-3:], ensure_ascii=False)
            article_json = _json.dumps(result["article_data"], ensure_ascii=False)
            try:
                include_intro = bool(query.session_id) and (not history) and not query.is_retry
                answer_text = await asyncio.to_thread(
                    formatter.format_response,
                    article_json,
                    text,
                    history_str,
                    include_intro=include_intro,
                )
            except Exception as e:
                logger.error(f"[Query] Formatter error: {e}")
                answer_text = result["article_data"].get("answer", result["answer_text"])
        else:
            answer_text = result.get("answer_text") or ""

        if not (answer_text and answer_text.strip()):
            answer_text = "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help."

        latency = (time.time() - start_time) * 1000
        logger.info(f"[Query] {answer_type} in {latency:.0f}ms | conf={confidence:.2f} | lang={user_language}")

        # Translate answer back to user's language
        answer_text_localized = None
        if user_language != "en" and answer_text:
            try:
                translated = await asyncio.to_thread(translator.translate, answer_text, "en", user_language)
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
                retrieval_score=float(result.get("confidence_raw") or result.get("confidence") or 0.0),
                answer_type=answer_type,
                source_id=result.get("source_id"),
                rewrite_attempted=True if rewrite_happened else False,
                rewritten_query=rewritten_text if rewrite_happened else None,
                latency_ms=round(latency, 2),
                created_at=int(time.time()),
            )
            db.add(log_entry)
            # Will commit later with history
        except Exception as e:
            logger.exception("[Query] DB log stage failed")
            db.rollback()

        if query.session_id:
            try:
                hist_entry = schema.SessionHistory(
                    session_id=query.session_id,
                    user_msg=text,
                    assistant_msg=answer_text
                )
                db.add(hist_entry)
            except Exception as e:
                logger.error(f"[Query] Failed to stage history: {e}")

        # Final commit for both log and history
        try:
            db.commit()
            if query_log_id is None and 'log_entry' in locals():
                query_log_id = log_entry.id
        except Exception as e:
            logger.error(f"[Query] Final commit failed: {e}")
            db.rollback()

        return api_models.QueryResponse(
            answer_text_en=answer_text,
            answer_text_localized=answer_text_localized,
            answer_type=answer_type,
            confidence=float(confidence),
            kb_version=query.kb_version,
            source_id=result.get("source_id"),
            clarification_categories=result.get("categories"),
            query_log_id=query_log_id,
            rlhf_top_source_id=result.get("rlhf_top_source_id"),
            rlhf_top_score=result.get("rlhf_top_score"),
        )

    except Exception:
        logger.exception("Query failed")
        return api_models.QueryResponse(
            answer_text_en="I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
            answer_text_localized=None,
            answer_type="NO_MATCH",
            confidence=0.4, # Set higher than 0 so Kiosk speaks it
            kb_version=getattr(query, "kb_version", 1),
            source_id=None,
            clarification_categories=None,
        )


@router.delete("/query/session/{session_id}")
async def end_session(session_id: str, db: Session = Depends(get_db)):
    try:
        db.query(schema.SessionHistory).filter(schema.SessionHistory.session_id == session_id).delete()
        db.commit()
        logger.info(f"Session {session_id} history deleted from DB.")
        return {"status": "success", "message": "Session ended."}
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        return {"status": "error", "message": str(e)}


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
