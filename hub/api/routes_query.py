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
from hub.retrieval import rewriter as query_rewriter
from hub.retrieval.normalizer import normalize_query
from hub.retrieval import formatter

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store: maps session_id → list of {user, assistant} dicts
session_history = {}


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
        rewrite_happened = False
        follow_up_prompt = result.get("follow_up_prompt")
        follow_up_intent = result.get("follow_up_intent")

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
                    logger.info(f"[Query] Rewrite retry: '{text[:40]}' -> '{candidate[:40]}' -> {retry_result['answer_type']}")
                    result = retry_result
                    rewritten_text = candidate
                    rewrite_happened = True
                    follow_up_prompt = result.get("follow_up_prompt")
                    follow_up_intent = result.get("follow_up_intent")
                except Exception as e:
                    logger.warning(f"[Query] Rewrite retry failed: {e}")

        answer_type = result["answer_type"]
        confidence = result["confidence"]

        if answer_type == "DIRECT_MATCH" and result.get("article_data"):
            history_str = ""
            # Do not use session history if this is a retry, as the LLM will see the disliked answer
            # and may lazily hallucinate and repeat the exact same response instead of using the new KB article.
            if query.session_id and query.session_id in session_history and not query.is_retry:
                history_str = json.dumps(session_history[query.session_id][-3:], ensure_ascii=False)
            article_json = json.dumps(result["article_data"], ensure_ascii=False)
            try:
                include_intro = bool(query.session_id) and (query.session_id not in session_history) and not query.is_retry
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
                created_at=int(_time.time()),
            )
            db.add(log_entry)
            db.commit()
            query_log_id = log_entry.id

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
