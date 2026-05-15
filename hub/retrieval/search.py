import os
import time
import logging
import json
from pathlib import Path
import numpy as np
from sqlalchemy.orm import Session
from typing import List, Optional
from hub.db import schema
from hub.retrieval.embedder import load_embedder, deserialize_embedding
from hub.retrieval import filter_policy
from hub.retrieval.normalizer import normalize_query
from hub.retrieval import inventory as inventory_module
from sentence_transformers import util

logger = logging.getLogger(__name__)


# ─── Taxonomy-backed clarification chip policy (Goal 7) ──────────────────────

_taxonomy_policy_cache = None


def _load_taxonomy_policy() -> dict:
    """Load taxonomy chip policy from hub/taxonomy/taxonomy_v1.json (cached)."""
    global _taxonomy_policy_cache
    if _taxonomy_policy_cache is not None:
        return _taxonomy_policy_cache
    try:
        hub_dir = Path(__file__).resolve().parents[1]
        path = hub_dir / "taxonomy" / "taxonomy_v1.json"
        with path.open("r", encoding="utf-8") as f:
            _taxonomy_policy_cache = json.load(f)
    except Exception:
        _taxonomy_policy_cache = {}
    return _taxonomy_policy_cache or {}


def _deterministic_clarification_node_ids(
    intent: str,
    inferred_taxonomy_node_ids: list[str],
    top_assigned_node_ids: set[str],
) -> list[str]:
    """
    Deterministic chip selection per Goal 7:
    - start with default set (max 3)
    - optionally replace ONE default with a conditional node when strongly indicated
    """
    policy = _load_taxonomy_policy().get("clarification_chip_defaults") or {}
    defaults = list(policy.get("default") or [])
    conditional = list(policy.get("conditional_replacements") or [])
    max_options = int(policy.get("max_options") or 3)

    # Strong indication signals: inferred nodes, top-k taxonomy assignments, or intent.
    conditional_signal_set = set(inferred_taxonomy_node_ids) | set(top_assigned_node_ids)

    # Intent -> likely conditional chip mapping (Goal 7 conditional additions list).
    intent_hint = {
        "safety": "rk.tax.safety_emergencies.emergency_procedures",
        "facilities": "rk.tax.basic_needs_daily_living.facilities_use",
        "sleeping": "rk.tax.basic_needs_daily_living.sleeping_rest_areas",
        "location": "rk.tax.location_navigation.in_shelter_locations",
    }.get(intent)
    if intent_hint:
        conditional_signal_set.add(intent_hint)

    chosen_conditional = None
    for node_id in conditional:
        if node_id in conditional_signal_set:
            chosen_conditional = node_id
            break

    chips = defaults[:max_options]
    if chosen_conditional and chosen_conditional not in chips and chips:
        # "Replace one default only when strongly indicated"
        chips[-1] = chosen_conditional

    # De-dupe while preserving order, enforce max.
    seen = set()
    out = []
    for nid in chips:
        if not nid or nid in seen:
            continue
        seen.add(nid)
        out.append(nid)
        if len(out) >= max_options:
            break
    return out

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

# Feedback-adjusted ranking settings (env-gated)
RLHF_ENABLED = os.environ.get("RESKIOSK_RLHF_ENABLED", "false").lower() == "true"
RLHF_ALPHA = float(os.environ.get("RESKIOSK_RLHF_ALPHA", 0.10))
RLHF_BIAS_TTL_SECS = int(os.environ.get("RESKIOSK_RLHF_BIAS_TTL_SECS", 1800))
# Explicit max delta cap (AC3): bias cannot move any single score by more than this,
# regardless of RLHF_ALPHA or the raw bias value.
RLHF_BIAS_MAX_DELTA = float(os.environ.get("RESKIOSK_RLHF_MAX_DELTA", 0.15))

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


CLARIFICATION_REASON_UNCLEAR_LOW_SCORE = "unclear_low_score"
CLARIFICATION_REASON_NOT_TRIGGERED = "not_triggered"
CLARIFICATION_REASON_COMPOUND_SHORTCUT = "compound_shortcut"
CLARIFICATION_REASON_HIGH_CONFIDENCE_INTENT = "high_confidence_intent"
CLARIFICATION_REASON_CONVERSATIONAL_INTENT = "conversational_intent"


def needs_clarification(
    query: str,
    top_k: List[RetrievalResult],
    intent: str,
    intent_confidence: float,
    is_compound: bool = False,
) -> tuple[bool, str]:
    """Return (should_clarify, reason_code).

    Reason codes are stable string constants; callers must log and persist them
    so operators can understand why clarification was or was not triggered.
    """
    if is_compound and intent_confidence >= INTENT_ACTION_THRESHOLD:
        return False, CLARIFICATION_REASON_COMPOUND_SHORTCUT
    if intent != "unclear" and intent_confidence >= INTENT_ACTION_THRESHOLD:
        return False, CLARIFICATION_REASON_HIGH_CONFIDENCE_INTENT
    if intent in ("greeting", "identity", "capability", "small_talk", "goodbye"):
        return False, CLARIFICATION_REASON_CONVERSATIONAL_INTENT
    best_retrieval_score = top_k[0].score if top_k else 0.0
    if intent == "unclear" and best_retrieval_score < CLARIFICATION_FLOOR:
        return True, CLARIFICATION_REASON_UNCLEAR_LOW_SCORE
    return False, CLARIFICATION_REASON_NOT_TRIGGERED


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


# --- Quarantine guard cache (TTL-based, same interval as bias cache) ---
_quarantined_ids_cache: Optional[set] = None
_quarantined_ids_loaded_at: float = 0.0


def _get_quarantined_item_ids(db: Session) -> set:
    """Return set of kb_article IDs currently quarantined or rejected.

    Bias must not be applied to these items (AC4). Cache is invalidated on
    the same TTL as the bias cache so both reflect the same operational state.
    """
    global _quarantined_ids_cache, _quarantined_ids_loaded_at
    now = time.time()
    if (
        _quarantined_ids_cache is None
        or _quarantined_ids_loaded_at == 0.0
        or now - _quarantined_ids_loaded_at > RLHF_BIAS_TTL_SECS
    ):
        try:
            rows = (
                db.query(schema.KBItemValidationStatus.kb_item_id)
                .filter(
                    schema.KBItemValidationStatus.status.in_(["quarantined", "rejected"])
                )
                .all()
            )
            _quarantined_ids_cache = {r[0] for r in rows}
            logger.info(f"[Bias] Quarantine guard loaded: {len(_quarantined_ids_cache)} blocked item(s).")
        except Exception:
            _quarantined_ids_cache = set()
        _quarantined_ids_loaded_at = now
    return _quarantined_ids_cache or set()


def invalidate_validation_quarantine_cache() -> None:
    """Clear TTL cache used for bias quarantine guard after validation status changes."""
    global _quarantined_ids_cache, _quarantined_ids_loaded_at
    _quarantined_ids_cache = None
    _quarantined_ids_loaded_at = 0.0
    logger.info("[Cache] Validation quarantine cache invalidated.")


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


def _load_corpus(db: Session, excluded_ids: frozenset[int] | None = None) -> dict:
    """Load and cache all enabled article embeddings as a numpy matrix.
    Articles are stored as plain dicts (not ORM objects) so the cache
    survives across different SQLAlchemy sessions.

    When *excluded_ids* is provided the cache is bypassed so that
    per-query validation-status exclusions are always respected.
    """
    global _corpus_cache

    # If no exclusion set is active, use the cache as before.
    if excluded_ids is None or len(excluded_ids) == 0:
        if _corpus_cache is not None:
            return _corpus_cache

    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == 1).all()
    embeddings = []
    meta = []
    skipped_by_policy = 0
    for art in articles:
        # Person 2: skip articles excluded by filter policy
        if excluded_ids and art.id in excluded_ids:
            skipped_by_policy += 1
            continue
        if art.embedding:
            vec = deserialize_embedding(art.embedding)
            if vec is not None:
                embeddings.append(vec)
                # Snapshot to plain dict while session is still open
                meta.append(_snapshot_article(art))

    corpus = {
        "matrix": np.stack(embeddings) if embeddings else None,
        "articles": meta
    }

    if skipped_by_policy > 0:
        logger.info(
            "[Cache] Loaded %d articles into corpus (skipped %d by filter policy).",
            len(meta), skipped_by_policy,
        )
    else:
        logger.info(f"[Cache] Loaded {len(meta)} articles into corpus cache.")

    # Only populate the long-lived cache when there are no per-query exclusions.
    if excluded_ids is None or len(excluded_ids) == 0:
        _corpus_cache = corpus

    return corpus


def _thresholds_for_language(lang: str) -> tuple[float, float]:
    if lang and lang != "en":
        return NON_EN_THRESHOLD, NON_EN_CLARIFICATION_FLOOR
    return THRESHOLD, CLARIFICATION_FLOOR


def retrieve(
    db: Session,
    query_english: str,
    is_retry: bool,
    selected_category: Optional[str] = None,
    selected_taxonomy_node_id: Optional[str] = None,
    exclude_source_ids: Optional[List[int]] = None,
    query_language: str = "en",
) -> dict:
    normalized_query = normalize_query(query_english, query_language)
    logger.info(f"[Retrieve] query='{normalized_query}' exclude_source_ids={exclude_source_ids}")

    # ── Person 2: compute validation-aware exclusion set ──────────────
    caller_exclude = set(exclude_source_ids) if exclude_source_ids else None
    policy_excluded_ids = filter_policy.compute_excluded_article_ids(
        db, extra_exclude_ids=caller_exclude,
    )

    # AC2: log UI-selected taxonomy node when present
    if selected_category:
        logger.info(f"[Filter] ui_category='{selected_category}'")

    ui_selection_source = None
    ui_selected_taxonomy_node_label = None
    if is_retry and selected_taxonomy_node_id:
        ui_selection_source = "taxonomy"
        try:
            node = (
                db.query(schema.TaxonomyNode)
                .filter(schema.TaxonomyNode.id == selected_taxonomy_node_id)
                .first()
            )
            if node and node.label:
                ui_selected_taxonomy_node_label = node.label
        except Exception:
            ui_selected_taxonomy_node_label = None
    elif is_retry and selected_category:
        ui_selection_source = "legacy_category"
    else:
        ui_selection_source = "none"

    # Will be computed after intent is finalized.
    inferred_taxonomy_node_ids: list[str] = []

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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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

    # Now that intent is finalized, compute inferred taxonomy nodes (deterministic, rank-ordered).
    try:
        rows = (
            db.query(schema.IntentTaxonomyMap)
            .filter(schema.IntentTaxonomyMap.intent_label == intent)
            .order_by(schema.IntentTaxonomyMap.rank.asc())
            .all()
        )
        inferred_taxonomy_node_ids = [r.taxonomy_node_id for r in rows if r.taxonomy_node_id]
    except Exception:
        inferred_taxonomy_node_ids = []

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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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

    # Phase 1 compatibility: if retry includes taxonomy node ID, enrich the query using its label.
    # This is additive and does not break legacy selected_category behavior.
    if is_retry and selected_taxonomy_node_id:
        try:
            node = (
                db.query(schema.TaxonomyNode)
                .filter(schema.TaxonomyNode.id == selected_taxonomy_node_id)
                .first()
            )
            if node and node.label:
                search_query = f"{search_query} {node.label}".strip()
        except Exception:
            # Non-fatal; fall back to text-only behavior.
            pass

    # 4. Embedding and corpus (guard so missing models/empty KB don't 500)
    try:
        embedder = load_embedder()
        query_vec = embedder.embed_text(search_query)
        corpus = _load_corpus(db, excluded_ids=policy_excluded_ids)
    except Exception as e:
        logger.exception("[Retrieve] Embedder or corpus failed")
        return {
            "answer_text": "I'm sorry, I couldn't process that. Please try again.",
            "answer_type": "NO_MATCH",
            "confidence": 0.0,
            "source_id": None,
            "categories": None,
            "article_data": None,
            "ui_selection_source": ui_selection_source,
            "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
            "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
            "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
            "ui_selection_source": ui_selection_source,
            "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
            "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
            "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
            "ui_selection_source": ui_selection_source,
            "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
            "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
            "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
            "intent": intent,
            "intent_confidence": intent_confidence,
        }

    # Keep a copy of raw cosine scores for logging and analysis.
    raw_scores = scores.copy()
    rlhf_top_source_id = None
    rlhf_top_score = None

    # Pre-compute article IDs aligned with corpus order (needed for bias + sort).
    article_ids = [art["id"] for art in corpus["articles"]]

    # Raw-cosine top-1 (always computed; used for bias_top1_changed and fallback).
    raw_top1_id = None
    if len(raw_scores) > 0:
        raw_best_idx = int(np.argmax(raw_scores))
        raw_top1_id = article_ids[raw_best_idx]

    # ── Feedback-adjusted ranking (separate bounded layer) ────────────────────
    # AC1: gated by RLHF_ENABLED env flag.
    # AC2: applied here, after baseline candidate scores are available.
    # AC3: bias delta is capped at RLHF_BIAS_MAX_DELTA before clamping to [0,1].
    # AC4: bias is zeroed for items with quarantined/rejected validation status.
    # AC5: per-item detail collected for logging.
    bias_applied_count = 0
    bias_top1_changed = False
    bias_detail: list = []      # [{id, baseline, bias_value, delta, final}] for top-k
    _bias_detail_map: dict = {} # keyed by article_id; trimmed to top-k after sort

    if RLHF_ENABLED:
        try:
            biases = _get_article_biases(db)
            quarantined = _get_quarantined_item_ids(db)

            for i, art_id in enumerate(article_ids):
                raw_b = biases.get(art_id, 0.0)
                # AC4: no bias for quarantined/rejected items.
                if art_id in quarantined:
                    raw_b = 0.0
                baseline = float(raw_scores[i])
                # AC3: clamp delta to [-RLHF_BIAS_MAX_DELTA, +RLHF_BIAS_MAX_DELTA].
                delta = max(-RLHF_BIAS_MAX_DELTA, min(RLHF_BIAS_MAX_DELTA, RLHF_ALPHA * raw_b))
                adj = max(0.0, min(1.0, baseline + delta))
                scores[i] = adj
                if raw_b != 0.0:
                    bias_applied_count += 1
                    _bias_detail_map[art_id] = {
                        "id": art_id,
                        "baseline": round(baseline, 6),
                        "bias_value": round(raw_b, 6),
                        "delta": round(delta, 6),
                        "final": round(adj, 6),
                    }

            if len(scores) > 0:
                best_idx = int(np.argmax(scores))
                rlhf_top_source_id = article_ids[best_idx]
                rlhf_top_score = float(scores[best_idx])
                bias_top1_changed = (raw_top1_id is not None and rlhf_top_source_id != raw_top1_id)
                logger.info(
                    f"[Bias] applied={RLHF_ENABLED} alpha={RLHF_ALPHA} max_delta={RLHF_BIAS_MAX_DELTA} "
                    f"applied_count={bias_applied_count} top1_changed={bias_top1_changed}"
                )
        except Exception:
            logger.exception("[Bias] Application failed; falling back to raw cosine scores")
            scores = raw_scores

    if not RLHF_ENABLED or rlhf_top_source_id is None:
        # Bias disabled or failed: shadow fields default to raw-cosine top-1.
        if raw_top1_id is not None:
            rlhf_top_source_id = raw_top1_id
            rlhf_top_score = float(raw_scores[int(np.argmax(raw_scores))])

    # AC6: deterministic sort — primary key is score descending, tie-break is
    # article_id ascending so ranking is reproducible for a fixed bias state.
    indexed = sorted(
        enumerate(scores),
        key=lambda x: (-x[1], article_ids[x[0]]),
    )
    top_indices = [idx for idx, _ in indexed[:5]]

    # Trim bias detail to top-k article IDs only (bounded log size).
    top_k_ids_ordered = [article_ids[i] for i in top_indices]
    bias_detail = [_bias_detail_map[aid] for aid in top_k_ids_ordered if aid in _bias_detail_map]
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
                "ui_selection_source": ui_selection_source,
                "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
                "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
                "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
                "intent": intent,
                "intent_confidence": intent_confidence,
                "rlhf_top_source_id": rlhf_top_source_id,
                "rlhf_top_score": rlhf_top_score,
                "bias_enabled": RLHF_ENABLED,
                "bias_applied_count": bias_applied_count,
                "bias_top1_changed": bias_top1_changed,
                "bias_detail": bias_detail,
            }

    best = top_k_results[0]

    # 5. Clarification gating (intent-aware)
    clarify = False
    clarify_reason = CLARIFICATION_REASON_NOT_TRIGGERED
    if not is_retry:
        clarify, clarify_reason = needs_clarification(
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
            "ui_selection_source": ui_selection_source,
            "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
            "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
            "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
            "bias_enabled": RLHF_ENABLED,
            "bias_applied_count": bias_applied_count,
            "bias_top1_changed": bias_top1_changed,
            "bias_detail": bias_detail,
            "is_compound": is_compound,
            "follow_up_prompt": follow_up_prompt,
            "follow_up_intent": follow_up_intent,
        }

    if best.score >= clarification_floor and clarify:
        cats = sorted(list({r.category for r in top_k_results if r.category}))
        if not cats:
            cats = ["General"]

        clarification_options = None
        try:
            top_ids = [r.article["id"] for r in top_k_results[:5] if r.article.get("id") is not None]
            top_assigned_node_ids: set[str] = set()
            if top_ids:
                assigned_rows = (
                    db.query(schema.KBItemTaxonomy.taxonomy_node_id)
                    .filter(schema.KBItemTaxonomy.kb_item_id.in_(top_ids))
                    .all()
                )
                top_assigned_node_ids = {r[0] for r in assigned_rows if r and r[0]}

            chip_node_ids = _deterministic_clarification_node_ids(
                intent=intent,
                inferred_taxonomy_node_ids=inferred_taxonomy_node_ids,
                top_assigned_node_ids=top_assigned_node_ids,
            )

            if chip_node_ids:
                node_rows = (
                    db.query(schema.TaxonomyNode.id, schema.TaxonomyNode.label)
                    .filter(schema.TaxonomyNode.id.in_(chip_node_ids))
                    .all()
                )
                label_by_id = {nid: lbl for nid, lbl in node_rows if nid and lbl}
                opts = []
                for nid in chip_node_ids:
                    lbl = label_by_id.get(nid)
                    if lbl:
                        opts.append({"id": nid, "label": lbl})
                if opts:
                    clarification_options = opts
        except Exception:
            clarification_options = None

        return {
            "answer_text": "Please clarify.",
            "answer_type": "NEEDS_CLARIFICATION",
            "confidence": best.score,
            "confidence_raw": best_raw_score,
            "source_id": best.article["id"],
            "clarification_trigger_reason": clarify_reason,
            "clarification_categories": cats,
            "clarification_options": clarification_options,
            "categories": cats,
            "ui_selection_source": ui_selection_source,
            "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
            "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
            "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
            "article_data": None,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "rlhf_top_source_id": rlhf_top_source_id,
            "rlhf_top_score": rlhf_top_score,
            "bias_enabled": RLHF_ENABLED,
            "bias_applied_count": bias_applied_count,
            "bias_top1_changed": bias_top1_changed,
            "bias_detail": bias_detail,
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
            "ui_selection_source": ui_selection_source,
            "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
            "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
            "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
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
            "bias_enabled": RLHF_ENABLED,
            "bias_applied_count": bias_applied_count,
            "bias_top1_changed": bias_top1_changed,
            "bias_detail": bias_detail,
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
        "ui_selection_source": ui_selection_source,
        "ui_selected_taxonomy_node_id": selected_taxonomy_node_id,
        "ui_selected_taxonomy_node_label": ui_selected_taxonomy_node_label,
        "inferred_taxonomy_node_ids": inferred_taxonomy_node_ids,
        "article_data": None,
        "intent": intent,
        "intent_confidence": intent_confidence,
        "rlhf_top_source_id": rlhf_top_source_id,
        "rlhf_top_score": rlhf_top_score,
        "bias_enabled": RLHF_ENABLED,
        "bias_applied_count": bias_applied_count,
        "bias_top1_changed": bias_top1_changed,
        "bias_detail": bias_detail,
        "is_compound": is_compound,
        "follow_up_prompt": None,
        "follow_up_intent": None,
    }
