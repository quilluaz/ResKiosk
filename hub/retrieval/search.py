import os
import time
import logging
import numpy as np
from sqlalchemy.orm import Session
from typing import List, Optional
from hub.db import schema
from hub.retrieval.embedder import load_embedder, deserialize_embedding
from hub.retrieval.normalizer import normalize_query
from hub.retrieval import inventory as inventory_module
from sentence_transformers import util

logger = logging.getLogger(__name__)

# Intent-based query enrichment keywords (used when intent is recognized with confidence)
INTENT_ENRICHMENT = {
    "greeting": "hello greeting",
    "identity": "kiosk assistant information",
    "capability": "help information services",
    "small_talk": "thanks okay",
    # Core shelter intents enriched with realistic query language.
    "food": "food meals schedule cafeteria canteen dining eat breakfast lunch dinner snacks",
    "medical": "medical doctor nurse health clinic first aid medicine",
    "registration": "registration sign up sign-up sign in check in intake wristband id card",
    "sleeping": "sleeping beds cots rest area sleeping area dormitory",
    "transportation": "bus shuttle transport ride leave departure",
    "safety": "safety emergency evacuation exit fire earthquake",
    "facilities": "bathroom restroom showers laundry charging wifi toilet",
    "lost_person": "lost missing family reunification missing person",
    "pets": "pets dog cat animal pet area",
    "donations": "donate donations donation drop off",
    "hours": "hours open close schedule opening closing time",
    "location": "address location directions building map",
    "goodbye": "goodbye bye thanks",
    "inventory": "supply stock available items request availability",
    "mental_health": "counseling stress trauma emotional mental psychological anxiety support",
    "legal_docs": "id documents legal aid certificate records assistance identification",
    "financial_aid": "vouchers cash aid assistance money financial relief fund",
    "hygiene": "soap shampoo toothbrush hygiene sanitation feminine products diapers clean",
    "departure": "leave go home shelter policy duration how long stay exit",
    "children": "children daycare school child baby infant kids family welfare",
    "special_needs": "wheelchair elderly disabled assistance mobility hearing impaired",
}

# Default thresholds tuned for realistic shelter questions; can still be overridden via env.
THRESHOLD = float(os.environ.get("RESKIOSK_SIM_THRESHOLD", 0.60))
CLARIFICATION_FLOOR = float(os.environ.get("RESKIOSK_CLARIFICATION_FLOOR", 0.40))
NON_EN_THRESHOLD = float(os.environ.get("RESKIOSK_NON_EN_SIM_THRESHOLD", 0.50))
NON_EN_CLARIFICATION_FLOOR = float(os.environ.get("RESKIOSK_NON_EN_CLARIFICATION_FLOOR", 0.38))

# Intent action threshold (enrichment + short-circuit + clarification suppression)
INTENT_ACTION_THRESHOLD = 0.35
COMPOUND_INTENT_MIN = float(os.environ.get("RESKIOSK_COMPOUND_INTENT_MIN", 0.35))
COMPOUND_GAP_MAX = float(os.environ.get("RESKIOSK_COMPOUND_GAP_MAX", 0.08))

INTENT_PRIORITY = {
    "safety": 100,
    "emergency": 100,
    "medical": 90,
    "children": 80,
    "special_needs": 80,
}

FOLLOW_UP_PROMPT_BY_INTENT = {
    "medical": "I can also help with medical support. Do you want that too?",
    "children": "I can also help with child-related support. Do you want that too?",
    "special_needs": "I can also help with special-needs support. Do you want that too?",
    "safety": "I can also help with safety guidance. Do you want that too?",
    "registration": "I can also help with registration steps. Do you want that too?",
    "sleeping": "I can also help with sleeping area information. Do you want that too?",
    "food": "I can also help with food and water schedules. Do you want that too?",
    "facilities": "I can also help with facilities information. Do you want that too?",
    "transportation": "I can also help with transportation details. Do you want that too?",
    "lost_person": "I can also help with missing-person reporting. Do you want that too?",
}

CLARIFICATION_CATEGORY_TO_INTENT = {
    "food & water": "food",
    "food and water": "food",
    "food": "food",
    "water": "food",
    "medical": "medical",
    "health": "medical",
    "registration": "registration",
    "sign in": "registration",
    "check in": "registration",
    "sleeping": "sleeping",
    "beds": "sleeping",
    "sleep": "sleeping",
    "facilities": "facilities",
    "restroom": "facilities",
    "bathroom": "facilities",
    "showers": "facilities",
    "laundry": "facilities",
    "transportation": "transportation",
    "safety": "safety",
    "security": "safety",
    "lost person": "lost_person",
    "lost family": "lost_person",
    "pets": "pets",
    "donations": "donations",
    "hours": "hours",
    "location": "location",
    "general": "general_info",
    "general info": "general_info",
    "mental health": "mental_health",
    "legal docs": "legal_docs",
    "legal": "legal_docs",
    "financial aid": "financial_aid",
    "hygiene": "hygiene",
    "departure": "departure",
    "leaving": "departure",
    "children": "children",
    "special needs": "special_needs",
}

# RLHF / bias settings (env-gated)
RLHF_ENABLED = os.environ.get("RESKIOSK_RLHF_ENABLED", "false").lower() == "true"
RLHF_ALPHA = float(os.environ.get("RESKIOSK_RLHF_ALPHA", 0.10))
RLHF_BIAS_TTL_SECS = int(os.environ.get("RESKIOSK_RLHF_BIAS_TTL_SECS", 1800))

# Intent classifier singleton, set by main.py at startup
_intent_classifier = None


def set_intent_classifier(classifier) -> None:
    global _intent_classifier
    _intent_classifier = classifier

class RetrievalResult:
    """Holds a cached article dict and its similarity score."""
    def __init__(self, article_dict: dict, score: float):
        self.article = article_dict  # plain dict, not ORM object
        self.score = score
        self.category = article_dict.get("category")


def needs_clarification(
    query: str,
    top_k: List[RetrievalResult],
    intent: str,
    intent_confidence: float,
    is_compound: bool = False,
) -> bool:
    """Only clarify when intent is unclear and best retrieval score is below CLARIFICATION_FLOOR."""
    if is_compound and intent_confidence >= INTENT_ACTION_THRESHOLD:
        return False
    if intent != "unclear" and intent_confidence >= INTENT_ACTION_THRESHOLD:
        return False
    if intent in ("greeting", "identity", "capability", "small_talk", "goodbye"):
        return False
    best_retrieval_score = top_k[0].score if top_k else 0.0
    return intent == "unclear" and best_retrieval_score < CLARIFICATION_FLOOR


def _intent_priority(intent: Optional[str]) -> int:
    if not intent:
        return 0
    return INTENT_PRIORITY.get(intent, 10)


def _resolve_compound_intents(
    top_intent: str,
    top_conf: float,
    second_intent: Optional[str],
    second_conf: float,
) -> tuple[str, float, Optional[str], float, bool]:
    if (
        second_intent
        and second_intent != top_intent
        and top_conf >= COMPOUND_INTENT_MIN
        and second_conf >= COMPOUND_INTENT_MIN
        and abs(top_conf - second_conf) <= COMPOUND_GAP_MAX
    ):
        if _intent_priority(second_intent) > _intent_priority(top_intent):
            return second_intent, second_conf, top_intent, top_conf, True
        return top_intent, top_conf, second_intent, second_conf, True
    return top_intent, top_conf, None, 0.0, False


# --- Fix 6: In-memory corpus cache ---
_corpus_cache = None  # None = stale, needs reload


def invalidate_corpus_cache():
    """Call this after any KB change (publish, create, update, delete)."""
    global _corpus_cache
    _corpus_cache = None
    logger.info("[Cache] Corpus cache invalidated.")


_shelter_config_cache = None


def get_shelter_config(db: Session) -> dict:
    """Load evac_info row as a flat dict; cached and invalidated on publish."""
    global _shelter_config_cache
    if _shelter_config_cache is not None:
        return _shelter_config_cache
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if row:
        _shelter_config_cache = {
            "food_schedule": row.food_schedule,
            "sleeping_zones": row.sleeping_zones,
            "medical_station": row.medical_station,
            "registration_steps": row.registration_steps,
            "announcements": row.announcements,
            "emergency_mode": row.emergency_mode,
            "metadata": row.info_metadata,
        }
    else:
        _shelter_config_cache = {}
    return _shelter_config_cache


def invalidate_shelter_config_cache():
    """Call on POST /admin/publish alongside corpus cache."""
    global _shelter_config_cache
    _shelter_config_cache = None
    logger.info("[Cache] Shelter config cache invalidated.")


# --- RLHF article-bias cache (TTL-based) ---
_article_biases_cache = None
_article_biases_loaded_at = 0.0


def _load_article_biases(db: Session) -> dict:
    """Load all article biases from DB into a simple dict {source_id: bias}."""
    rows = db.query(schema.ArticleBias).all()
    biases = {row.source_id: float(row.bias) for row in rows}
    logger.info(f"[RLHF] Loaded {len(biases)} article biases from DB.")
    return biases


def _get_article_biases(db: Session) -> dict:
    """Return cached article biases, reloading from DB when TTL expires."""
    global _article_biases_cache, _article_biases_loaded_at
    now = time.time()
    if (
        _article_biases_cache is None
        or _article_biases_loaded_at == 0.0
        or now - _article_biases_loaded_at > RLHF_BIAS_TTL_SECS
    ):
        _article_biases_cache = _load_article_biases(db)
        _article_biases_loaded_at = now
    return _article_biases_cache or {}


def _snapshot_article(art: schema.KBArticle) -> dict:
    """Eagerly copy all needed fields from an ORM object into a plain dict.
    Prevents DetachedInstanceError when the cache outlives the session."""
    raw_tags = getattr(art, "tags", "") or ""
    tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
    return {
        "id": art.id,
        "question": art.question,
        "answer": art.answer,
        "category": art.category,
        "tags": tags_list,
    }


def _load_corpus(db: Session) -> dict:
    """Load and cache all enabled article embeddings as a numpy matrix.
    Articles are stored as plain dicts (not ORM objects) so the cache
    survives across different SQLAlchemy sessions."""
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    
    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == 1).all()
    embeddings = []
    meta = []
    for art in articles:
        if art.embedding:
            vec = deserialize_embedding(art.embedding)
            if vec is not None:
                embeddings.append(vec)
                # Snapshot to plain dict while session is still open
                meta.append(_snapshot_article(art))
    
    _corpus_cache = {
        "matrix": np.stack(embeddings) if embeddings else None,
        "articles": meta
    }
    logger.info(f"[Cache] Loaded {len(meta)} articles into corpus cache.")
    return _corpus_cache


def _thresholds_for_language(lang: str) -> tuple[float, float]:
    if lang and lang != "en":
        return NON_EN_THRESHOLD, NON_EN_CLARIFICATION_FLOOR
    return THRESHOLD, CLARIFICATION_FLOOR


def retrieve(
    db: Session,
    query_english: str,
    is_retry: bool,
    selected_category: Optional[str] = None,
    exclude_source_ids: Optional[List[int]] = None,
    query_language: str = "en",
) -> dict:
    normalized_query = normalize_query(query_english, query_language)
    logger.info(f"[Retrieve] query='{normalized_query}' exclude_source_ids={exclude_source_ids}")
    # AC2: log UI-selected taxonomy node when present
    if selected_category:
        logger.info(f"[Filter] ui_category='{selected_category}'")

    # 1. Inventory check (phrase triggers; no embedding)
    try:
        shelter_config = get_shelter_config(db)
        inventory_answer = inventory_module.check_inventory(normalized_query, shelter_config)
        if inventory_answer:
            return {
                "answer_text": inventory_answer,
                "answer_type": "DIRECT_MATCH",
                "confidence": 1.0,
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": "inventory",
                "intent_confidence": 1.0,
            }
    except Exception as e:
        logger.warning(f"[Retrieve] Shelter config/inventory failed: {e}")

    # 3. Classify intent and optionally enrich query
    intent, intent_confidence = "unclear", 0.0
    second_intent, second_confidence = None, 0.0
    compound_secondary_intent = None
    is_compound = False
    if _intent_classifier:
        try:
            if hasattr(_intent_classifier, "classify_top2"):
                intent, intent_confidence, second_intent, second_confidence = _intent_classifier.classify_top2(normalized_query)
                logger.info(
                    f"[Retrieve] intent={intent} confidence={intent_confidence:.4f} second={second_intent} second_conf={second_confidence:.4f}"
                )
            else:
                intent, intent_confidence = _intent_classifier.classify(normalized_query)
                logger.info(f"[Retrieve] intent={intent} confidence={intent_confidence:.4f}")
        except Exception as e:
            logger.warning(f"[Retrieve] Intent classification failed: {e}")

    intent, intent_confidence, compound_secondary_intent, _, is_compound = _resolve_compound_intents(
        intent,
        intent_confidence,
        second_intent,
        second_confidence,
    )
    if is_compound:
        logger.info(
            f"[Retrieve] compound=True primary={intent}({intent_confidence:.4f}) secondary={compound_secondary_intent}"
        )

    retry_category_intent = None
    if is_retry and selected_category:
        retry_category_intent = CLARIFICATION_CATEGORY_TO_INTENT.get((selected_category or "").strip().lower())
        if retry_category_intent:
            intent = retry_category_intent
            intent_confidence = max(intent_confidence, INTENT_ACTION_THRESHOLD)
            second_intent = None
            second_confidence = 0.0
            compound_secondary_intent = None
            is_compound = False
            logger.info(f"[Retrieve] retry category override -> intent={intent}")

    # 3a. Short-circuit for simple conversational intents (no KB lookup)
    # Skip short-circuits when retry + selected category is forcing a secondary intent answer.
    if intent != "unclear" and intent_confidence >= INTENT_ACTION_THRESHOLD and not (is_retry and retry_category_intent):
        if intent == "greeting":
            return {
                "answer_text": "Hello. I can help you with questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. What would you like to ask?",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "identity":
            return {
                "answer_text": "This is ResKiosk, an information kiosk for this evacuation center. It can answer questions about registration, food and water, medical help, sleeping areas, transportation, safety, and other basic services.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "capability":
            return {
                "answer_text": "I can tell you about registration, food and water, medical help, sleeping areas, transportation, safety information, and other services available in this shelter.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "small_talk":
            return {
                "answer_text": "You're welcome. If you need anything else, you can ask me about registration, food, medical help, sleeping areas, transportation, and other services in this shelter.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }
        if intent == "goodbye":
            return {
                "answer_text": "Okay. If you have more questions later, you can come back and ask me again.",
                "answer_type": "DIRECT_MATCH",
                "confidence": float(intent_confidence),
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
            }

    search_query = normalized_query
    if intent != "unclear" and intent_confidence >= INTENT_ACTION_THRESHOLD and intent in INTENT_ENRICHMENT:
        search_query = f"{normalized_query} {INTENT_ENRICHMENT[intent]}"
        enrichment_secondary = compound_secondary_intent
        if not enrichment_secondary and second_intent and second_intent != intent and second_confidence >= INTENT_ACTION_THRESHOLD:
            enrichment_secondary = second_intent
        if enrichment_secondary and enrichment_secondary in INTENT_ENRICHMENT:
            search_query = f"{search_query} {INTENT_ENRICHMENT[enrichment_secondary]}"
    if is_retry and selected_category:
        mapped = CLARIFICATION_CATEGORY_TO_INTENT.get((selected_category or "").strip().lower())
        if mapped and mapped in INTENT_ENRICHMENT:
            search_query = f"{search_query} {INTENT_ENRICHMENT[mapped]}"
        else:
            search_query = f"{search_query} {selected_category}"
    # AC3: log inferred taxonomy node when intent drives candidate retrieval
    if intent != "unclear" and intent_confidence >= INTENT_ACTION_THRESHOLD:
        logger.info(f"[Filter] inferred_taxonomy='{intent}' confidence={intent_confidence:.4f}")

    # 4. Embedding and corpus (guard so missing models/empty KB don't 500)
    try:
        embedder = load_embedder()
        query_vec = embedder.embed_text(search_query)
        corpus = _load_corpus(db)
    except Exception as e:
        logger.exception("[Retrieve] Embedder or corpus failed")
        return {
            "answer_text": "I'm sorry, I couldn't process that. Please try again.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    if corpus["matrix"] is None or len(corpus["articles"]) == 0:
        return {
            "answer_text": "No knowledge base entries available.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    try:
        scores = util.cos_sim(query_vec, corpus["matrix"])[0].numpy()
    except Exception as e:
        logger.exception("[Retrieve] Similarity computation failed")
        return {
            "answer_text": "I'm sorry, I couldn't process that. Please try again.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    # Keep a copy of raw cosine scores for logging and analysis.
    raw_scores = scores.copy()
    rlhf_top_source_id = None
    rlhf_top_score = None

    # Apply RLHF bias adjustment when enabled; otherwise leave scores unchanged.
    if RLHF_ENABLED:
        try:
            biases = _get_article_biases(db)
            article_ids = [art["id"] for art in corpus["articles"]]
            for i, art_id in enumerate(article_ids):
                b = biases.get(art_id, 0.0)
                adj = float(raw_scores[i]) + RLHF_ALPHA * b
                # Clamp to cosine range [0, 1]
                scores[i] = max(0.0, min(1.0, adj))
            if len(scores) > 0:
                best_idx = int(np.argmax(scores))
                rlhf_top_source_id = article_ids[best_idx]
                rlhf_top_score = float(scores[best_idx])
        except Exception as e:
            logger.exception("[RLHF] Bias application failed; falling back to raw cosine scores")
            scores = raw_scores

    if not RLHF_ENABLED or rlhf_top_source_id is None:
        # RLHF disabled or failed: default RLHF shadow fields to raw-cosine top-1.
        if len(raw_scores) > 0:
            raw_best_idx = int(np.argmax(raw_scores))
            rlhf_top_source_id = corpus["articles"][raw_best_idx]["id"]
            rlhf_top_score = float(raw_scores[raw_best_idx])

    top_indices = np.argsort(scores)[::-1][:5]
    top_k_results = []
    for idx in top_indices:
        art_dict = corpus["articles"][idx]
        score = float(scores[idx])
        top_k_results.append(RetrievalResult(art_dict, score))

    # AC4: total corpus candidates and how many scored into top-k
    candidates_total = len(corpus["articles"])
    logger.info(f"[Filter] candidates_total={candidates_total} top_k_scored={len(top_k_results)}")
    for i, r in enumerate(top_k_results[:3]):
        logger.info(f"[Search] #{i+1} score={r.score:.4f} question='{r.article['question'][:60]}' cat={r.category}")

    # Raw best score (for logging) uses raw cosine; gating may use adjusted scores.
    if len(raw_scores) > 0:
        try:
            best_raw_score = float(raw_scores[int(np.argmax(raw_scores))])
        except Exception:
            best_raw_score = float(best.score)
    else:
        # Fallback: no scores (should not normally happen here)
        best_raw_score = 0.0

    # AC1 + AC4: hard rule — exclude_source_ids filter
    if exclude_source_ids:
        count_before = len(top_k_results)
        exclude_set = set(exclude_source_ids)
        top_k_results = [r for r in top_k_results if r.article["id"] not in exclude_set]
        count_after = len(top_k_results)
        logger.info(
            f"[Filter] rule=exclude_ids before={count_before} after={count_after} "
            f"removed={count_before - count_after} excluded_ids={list(exclude_set)}"
        )
        if not top_k_results:
            # AC5: all candidates excluded — fallback to NO_MATCH
            logger.info("[Filter] fallback=all_candidates_excluded outcome=NO_MATCH")
            return {
                "answer_text": "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
                "answer_type": "NO_MATCH",
                "confidence": best_raw_score,
                "confidence_raw": best_raw_score,
                "source_id": None,
                "categories": None,
                "article_data": None,
                "intent": intent,
                "intent_confidence": intent_confidence,
                "rlhf_top_source_id": rlhf_top_source_id,
                "rlhf_top_score": rlhf_top_score,
            }

    best = top_k_results[0]

    # 5. Clarification gating (intent-aware)
    clarify = False
    if not is_retry:
        clarify = needs_clarification(
            normalized_query,
            top_k_results,
            intent,
            intent_confidence,
            is_compound=is_compound,
        )

    threshold, clarification_floor = _thresholds_for_language(query_language)
    # 6. Gating: >= threshold DIRECT_MATCH; clarify below floor; else NO_MATCH
    if best.score >= threshold:
        follow_up_intent = compound_secondary_intent if is_compound else None
        follow_up_prompt = FOLLOW_UP_PROMPT_BY_INTENT.get(follow_up_intent) if follow_up_intent else None
        return {
            "answer_text": best.article["answer"],
            "answer_type": "DIRECT_MATCH",
            "confidence": best.score,
            "confidence_raw": best_raw_score,
            "source_id": best.article["id"],
            "categories": None,
            "article_data": {
                "question": best.article["question"],
                "answer": best.article["answer"],
                "category": best.article["category"],
                "tags": best.article.get("tags", [])
            },
            "intent": intent,
            "intent_confidence": intent_confidence,
            "rlhf_top_source_id": rlhf_top_source_id,
            "rlhf_top_score": rlhf_top_score,
            "is_compound": is_compound,
            "follow_up_prompt": follow_up_prompt,
            "follow_up_intent": follow_up_intent,
        }

    if best.score >= clarification_floor and clarify:
        cats = sorted(list({r.category for r in top_k_results if r.category}))
        if not cats:
            cats = ["General"]
        # AC5: score below threshold; clarification triggered
        logger.info(
            f"[Filter] fallback=clarification_gate best_score={best.score:.4f} "
            f"threshold={threshold} floor={clarification_floor}"
        )
        return {
            "answer_text": "Please clarify.",
            "answer_type": "NEEDS_CLARIFICATION",
            "confidence": best.score,
            "confidence_raw": best_raw_score,
            "source_id": best.article["id"],
            "clarification_categories": cats,
            "categories": cats,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "rlhf_top_source_id": rlhf_top_source_id,
            "rlhf_top_score": rlhf_top_score,
            "is_compound": is_compound,
            "follow_up_prompt": None,
            "follow_up_intent": None,
        }

    # 0.45-0.65: use best match; < 0.45 or no clarify: fixed fallback
    if best.score >= clarification_floor:
        # AC5: sub-threshold direct match (above floor, below threshold, clarification not triggered)
        logger.info(
            f"[Filter] fallback=sub_threshold_direct best_score={best.score:.4f} "
            f"threshold={threshold} floor={clarification_floor}"
        )
        follow_up_intent = compound_secondary_intent if is_compound else None
        follow_up_prompt = FOLLOW_UP_PROMPT_BY_INTENT.get(follow_up_intent) if follow_up_intent else None
        return {
            "answer_text": best.article["answer"],
            "answer_type": "DIRECT_MATCH",
            "confidence": best.score,
            "confidence_raw": best_raw_score,
            "source_id": best.article["id"],
            "categories": None,
            "article_data": {
                "question": best.article["question"],
                "answer": best.article["answer"],
                "category": best.article["category"],
                "tags": best.article.get("tags", [])
            },
            "intent": intent,
            "intent_confidence": intent_confidence,
            "rlhf_top_source_id": rlhf_top_source_id,
            "rlhf_top_score": rlhf_top_score,
            "is_compound": is_compound,
            "follow_up_prompt": follow_up_prompt,
            "follow_up_intent": follow_up_intent,
        }

    # AC5: score below clarification floor — true NO_MATCH
    logger.info(
        f"[Filter] fallback=no_match best_score={best.score:.4f} "
        f"threshold={threshold} floor={clarification_floor}"
    )
    return {
        "answer_text": "I am here to answer questions about registration, food, medical help, sleeping areas, transportation, safety, and other services in this shelter. Please ask about one of these topics or see a volunteer for more help.",
        "answer_type": "NO_MATCH",
        "confidence": best.score,
        "confidence_raw": best_raw_score,
        "source_id": None,
        "categories": None,
        "article_data": None,
        "intent": intent,
        "intent_confidence": intent_confidence,
        "rlhf_top_source_id": rlhf_top_source_id,
        "rlhf_top_score": rlhf_top_score,
        "is_compound": is_compound,
        "follow_up_prompt": None,
        "follow_up_intent": None,
    }
