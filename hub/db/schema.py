from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, LargeBinary, ForeignKey, DateTime,
    Boolean
)
from hub.db.session import Base

#make sure remove duplicates
class QueryLog(Base):
    """Logs every voice query made by kiosks."""
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=True)
    kiosk_id = Column(String)
    # Optional shadow fields for RLHF analysis (what RLHF would have picked)
    rlhf_top_source_id = Column(Integer, nullable=True)
    rlhf_top_score = Column(Float, nullable=True)
    transcript_original = Column(Text)
    transcript_english = Column(Text, nullable=True)
    raw_transcript = Column(Text, nullable=True)       # query text passed to retrieve (after translation)
    normalized_transcript = Column(Text, nullable=True)  # after normalize_query
    language = Column(String)
    kb_version = Column(Integer)
    retrieval_score = Column(Float, nullable=True)
    answer_type = Column(String)
    source_id = Column(Integer, nullable=True)
    rewrite_attempted = Column(Boolean, default=False)  # Stored as 0/1 in SQLite
    rewritten_query = Column(Text, nullable=True)
    formatter_mode = Column(String, nullable=True)  # cloud|local
    stt_mode = Column(String, nullable=True)        # kiosk-reported: cloud|local
    tts_mode = Column(String, nullable=True)        # kiosk-reported: cloud|local
    connectivity_state = Column(String, nullable=True)  # ONLINE|OFFLINE
    cloud_consent_mode = Column(String, nullable=False, default="disabled")
    latency_ms = Column(Float)
    # Goal 7 (taxonomy) observability fields (additive; safe for older clients)
    ui_selection_source = Column(String, nullable=True)  # taxonomy|legacy_category|none
    ui_selected_taxonomy_node_id = Column(String, nullable=True)
    ui_selected_taxonomy_node_label = Column(Text, nullable=True)
    inferred_taxonomy_node_ids = Column(Text, nullable=True)  # JSON array string
    widening_step = Column(String, nullable=True)  # none|remove_inferred|broaden_ui|safe_fallback
    widening_reason = Column(Text, nullable=True)
    # Goal 6 / Story 6 — clarification lifecycle logging
    clarification_triggered = Column(Boolean, nullable=True)
    clarification_trigger_reason = Column(String, nullable=True)   # stable reason code constant
    clarification_options_shown = Column(Text, nullable=True)       # JSON: [{id, label}, ...]
    pipeline_stage_log = Column(Text, nullable=True)               # JSON: ordered list of stage names
    # Slice 6A Story 1: structured query log schema additions
    intent_label = Column(String, nullable=True)
    intent_confidence = Column(Float, nullable=True)
    clarification_categories_offered = Column(Text, nullable=True)  # JSON array string
    clarification_node_id_selected = Column(String, nullable=True)
    # Hybrid retrieval contribution fields (populated by Slice 4 Story 5)
    lexical_top_k_ids = Column(Text, nullable=True)      # JSON array of article IDs (top-5)
    lexical_top_k_scores = Column(Text, nullable=True)   # JSON array of BM25 scores
    lexical_top_k_ranks = Column(Text, nullable=True)    # JSON array of ranks
    lexical_latency_ms = Column(Float, nullable=True)
    vector_top_k_ids = Column(Text, nullable=True)       # JSON array of article IDs (top-5)
    vector_top_k_scores = Column(Text, nullable=True)    # JSON array of cosine scores
    vector_top_k_ranks = Column(Text, nullable=True)     # JSON array of ranks
    fusion_strategy = Column(String, nullable=True)      # e.g. "rrf"
    fusion_top_k_ids = Column(Text, nullable=True)       # JSON array of fused IDs (top-5)
    fusion_top_k_scores = Column(Text, nullable=True)    # JSON array of fusion scores
    fusion_top_k_ranks = Column(Text, nullable=True)     # JSON array of ranks
    # Failure / fallback fields (populated by Slice 6A Story 8)
    fallback_reason = Column(String, nullable=True)      # no_results|low_confidence|validation_blocked|retrieval_error|rewrite_error
    failed_stage = Column(String, nullable=True)         # normalize|intent|retrieve|clarification_gate|rewrite|retrieve_retry
    created_at = Column(Integer)  # Unix timestamp


class FeedbackLog(Base):
    """Per-query feedback from kiosks used for RLHF-style ranking."""
    __tablename__ = "feedback_logs"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, nullable=True)
    query_log_id = Column(Integer, nullable=True)
    source_id = Column(Integer, nullable=True)
    label = Column(Integer, nullable=True)  # -1=inaccurate, +1=thumbs-up (future v2)
    language = Column(String, nullable=True)
    kiosk_id = Column(String, nullable=True)
    center_id = Column(String, nullable=True)


class ArticleBias(Base):
    """Per-article bias value learned from FeedbackLog."""
    __tablename__ = "article_biases"
    source_id = Column(Integer, primary_key=True, index=True)
    bias = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClarificationResolution(Base):
    """Records when a user resolves ambiguity by selecting a clarification chip."""
    __tablename__ = "clarification_resolutions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False)
    raw_transcript = Column(Text, nullable=True)
    resolved_intent = Column(String, nullable=False)
    language = Column(String, nullable=True)
    # Chip selection — stable ID (taxonomy node ID or legacy category string)
    selected_option_id = Column(String, nullable=True)
    # Human-readable label for the selected chip (stored so it's readable without a taxonomy join)
    selected_option_label = Column(String, nullable=True)
    # FK to query_logs so this row can be joined to the full request context
    query_log_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HubIdentity(Base):
    """Single-row table: this hub's persistent ID. Never exposed to operator editing."""
    __tablename__ = "hub_identity"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hub_id = Column(Integer)
    hub_name = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class KBArticle(Base):
    """Main searchable Knowledge Base — all answers come from here."""
    __tablename__ = "kb_articles"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    question     = Column(Text, nullable=False)
    answer       = Column(Text, nullable=False)
    category     = Column(Text)
    tags         = Column(Text)                       # Comma-separated
    enabled      = Column(Integer, default=1)         # 1 = active, 0 = disabled
    source       = Column(Text, default="manual")
    created_at   = Column(Integer)                    # Unix timestamp
    last_updated = Column(Integer)                    # Unix timestamp
    embedding    = Column(LargeBinary, nullable=True) # Serialized vector
    status       = Column(String, nullable=True)
    created_by   = Column(Text, default="System Generated")
    updated_by   = Column(Text, nullable=True)
    # Goal 7 (Story 2): filterable metadata (additive)
    authority    = Column(String, nullable=True)  # official|shelter_staff|volunteer|unknown
    scope        = Column(String, nullable=True)  # shelter_local|general
    center_id    = Column(String, nullable=True)  # future-friendly scoping
    hub_id       = Column(String, nullable=True)  # future-friendly scoping


class EvacInfo(Base):
    """Single-row table for all editable shelter operations data."""
    __tablename__ = "evac_info"

    id                 = Column(Integer, primary_key=True, default=1)
    food_schedule      = Column(Text)
    food_distribution_location = Column(Text)
    sleeping_zones     = Column(Text)
    medical_station    = Column(Text)
    registration_steps = Column(Text)
    announcements      = Column(Text)
    emergency_mode     = Column(Text)
    last_updated       = Column(Text)
    info_metadata           = Column(Text)  # JSON for dynamic console forms


class NetworkConfig(Base):
    """Stores the hub's local Wi-Fi and server configuration."""
    __tablename__ = "network_config"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    network_mode = Column(Text)   # 'hotspot' or 'router'
    ip_override  = Column(Text)
    port         = Column(Integer)
    cloud_enabled = Column(Integer, default=0)
    cloud_user_overridden = Column(Integer, default=0)
    cloud_last_changed_at = Column(Integer, nullable=True)
    last_updated = Column(Integer)  # Unix timestamp


class SystemVersion(Base):
    """Tracks the current Knowledge Base version so kiosks know when to refresh."""
    __tablename__ = "system_version"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    kb_version     = Column(Integer)
    last_published = Column(Integer)  # Unix timestamp



class Hub(Base):
    """Registry of all Shelter Hubs / evacuation centers."""
    __tablename__ = "hub"

    hub_id     = Column(Integer, primary_key=True, autoincrement=True)
    device_id  = Column(Text, unique=True)   # Unique hardware/device identifier
    hub_name   = Column(Text, nullable=False, unique=True)
    location   = Column(Text)
    created_at = Column(Integer)  # Unix timestamp


class HubMessage(Base):
    """Central table for all communication between hubs."""
    __tablename__ = "hub_messages"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    category_id    = Column(Integer, ForeignKey("categories.category_id"))
    source_hub_id  = Column(Integer, ForeignKey("hub.hub_id"))
    target_hub_id  = Column(Integer, ForeignKey("hub.hub_id"), nullable=True)  # NULL = broadcast
    subject        = Column(Text)
    content        = Column(Text)
    priority       = Column(Text)  # 'normal', 'urgent', 'emergency'
    status         = Column(Text)  # 'pending', 'delivered', 'read', 'published', 'rejected'
    sent_at        = Column(Integer)  # Unix timestamp
    received_at    = Column(Integer)  # Unix timestamp
    published_at   = Column(Integer)  # Unix timestamp
    location       = Column(Text)
    created_by     = Column(Text)     # Should eventually be FK to user.user_id
    hop_count      = Column(Integer)
    ttl            = Column(Integer)
    received_via   = Column(Text)     # 'lora', 'manual', 'wifi-local'
    details        = Column(Text)     # JSON for category-specific fields


class LoraConfig(Base):
    """Persisted ESP+LoRa connection settings so the hub can auto-reconnect."""
    __tablename__ = "lora_config"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    port            = Column(Text)
    baud_rate       = Column(Integer, default=115200)
    connection_type = Column(Text, default="serial")   # 'serial' or 'bluetooth'
    auto_connect    = Column(Integer, default=0)        # 1 = reconnect on startup
    last_connected  = Column(Integer)                   # Unix timestamp




class User(Base):
    """Admin users who can log in and manage the system."""
    __tablename__ = "user"

    user_id       = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(Text, unique=True, nullable=False)
    fname         = Column(Text)
    mname         = Column(Text)
    lname         = Column(Text)
    password      = Column(Text)   # bcrypt-hashed
    is_first_login = Column(Boolean, default=True, nullable=False)
    created_at    = Column(Integer)  # Unix timestamp



class Kiosk(Base):
    """Physical kiosk/tablet devices registered under a hub."""
    __tablename__ = "kiosk"

    kiosk_id   = Column(Integer, primary_key=True, autoincrement=True)
    hub_id     = Column(Integer, ForeignKey("hub.hub_id"), nullable=False)
    kiosk_name = Column(Text)
    location   = Column(Text)
    status     = Column(Text)   # 'online', 'offline', 'maintenance'
    last_seen  = Column(Integer)  # Unix timestamp
    created_at = Column(Integer)  # Unix timestamp


class Category(Base):
    """Preloaded message categories for hub-to-hub messaging."""
    __tablename__ = "categories"

    category_id   = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(Text, nullable=False, unique=True)
    description   = Column(Text)


class EmergencyAlert(Base):
    """Emergency button activations sent from kiosks."""
    __tablename__ = "emergency_alerts"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    kiosk_id       = Column(Text, nullable=False)
    kiosk_location = Column(Text, nullable=False)  # Snapshot at alert time
    hub_id         = Column(Text, nullable=True)
    transcript     = Column(Text)
    language       = Column(Text, default="en")
    timestamp      = Column(Integer, nullable=False)  # Unix ms
    # New lifecycle fields (status is authoritative; resolved kept for backward compatibility)
    status           = Column(Text, default="ACTIVE")  # ACTIVE | ACKNOWLEDGED | RESPONDING | RESOLVED | DISMISSED
    tier             = Column(Integer, default=1)      # 1 = immediate, 2 = confirmed
    alert_id_local   = Column(Text, nullable=True)     # kiosk UUID for dedup
    acknowledged_at  = Column(Integer, nullable=True)  # Unix ms
    responding_at    = Column(Integer, nullable=True)  # Unix ms
    dismissed_by_kiosk = Column(Integer, default=0)
    dismissed_at     = Column(Integer, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_by      = Column(Text, nullable=True)
    retry_count      = Column(Integer, default=0)
    resolved         = Column(Integer, default=0)      # 0 = open, 1 = resolved
    resolved_at      = Column(Integer, nullable=True)  # Unix ms


# ─── New tables (exist in merged DB but had no ORM model) ─────────────────


class KBMeta(Base):
    """KB metadata — tracks version info separately from SystemVersion."""
    __tablename__ = "kb_meta"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    kb_version = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow)


class KioskRegistry(Base):
    """Auto-discovered kiosks on the network (separate from the managed Kiosk table)."""
    __tablename__ = "kiosk_registry"

    kiosk_id   = Column(Text, primary_key=True)
    kiosk_name = Column(Text)
    ip_address = Column(Text)
    hub_id     = Column(Text, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen  = Column(DateTime, default=datetime.utcnow)


class StructuredConfig(Base):
    """Key-value configuration store for hub settings."""
    __tablename__ = "structured_config"

    key        = Column(String, primary_key=True)
    value      = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class FAQTracker(Base):
    """Tracks frequently asked questions grouped by KB article answer (source_id)."""
    __tablename__ = "faq_tracker"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    source_id           = Column(Integer, nullable=False, unique=True, index=True)  # KB article ID
    source_question     = Column(Text, nullable=True)   # KB article question (for display)
    source_answer       = Column(Text, nullable=True)   # KB article answer snippet (for display)
    question_normalized = Column(Text, nullable=True)    # Last user query (lowercased)
    question_display    = Column(Text, nullable=True)    # Last user query (original case)
    language            = Column(String, nullable=True)
    count               = Column(Integer, nullable=False, default=1)
    first_asked_at      = Column(Integer)   # Unix timestamp
    last_asked_at       = Column(Integer)   # Unix timestamp
    kiosk_id            = Column(String, nullable=True)
    answer_type         = Column(String, nullable=True)


# ─── Taxonomy (Goal 7 / Story 1) ──────────────────────────────────────────────


class TaxonomyNode(Base):
    """Controlled taxonomy node with a stable string ID (rk.tax.*)."""
    __tablename__ = "taxonomy_nodes"

    id = Column(String, primary_key=True)  # stable ID like rk.tax.health_medical.medical_services
    label = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    sort_order = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaxonomyEdge(Base):
    """DAG edge (parent -> child). Multi-parent allowed; must remain acyclic by policy."""
    __tablename__ = "taxonomy_edges"

    parent_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    child_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KBItemTaxonomy(Base):
    """Assignment of a KB article to one or more taxonomy nodes."""
    __tablename__ = "kb_item_taxonomy"

    kb_item_id = Column(Integer, ForeignKey("kb_articles.id"), primary_key=True)
    taxonomy_node_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    source = Column(Text, nullable=True)  # manual | import | legacy_category | auto
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntentTaxonomyMap(Base):
    """Normalized intent -> taxonomy mapping (multiple rows per intent label)."""
    __tablename__ = "intent_taxonomy_map"

    intent_label = Column(String, primary_key=True)
    taxonomy_node_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    rank = Column(Integer, default=1)  # 1=primary, 2+=secondary
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Goal 8 / Slice 3 Story 2 — Metadata validation storage ──────────────────


class KBPublishAttempt(Base):
    """One row per publish attempt; anchors validation results and review decisions
    to a specific KB version and point in time.

    status values: pass | blocked | partial
      pass    — all items approved; publish proceeded
      blocked — one or more quarantined/rejected items; publish was halted
      partial — publish proceeded with quarantined items excluded (auditable mode)
    """
    __tablename__ = "kb_publish_attempts"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    kb_version     = Column(Integer, nullable=False)         # intended version after publish
    status         = Column(String, nullable=False)          # pass|blocked|partial
    total_items    = Column(Integer, nullable=True)
    approved_count = Column(Integer, nullable=True)
    quarantined_count = Column(Integer, nullable=True)
    rejected_count = Column(Integer, nullable=True)
    attempted_by   = Column(String, nullable=True)           # username of initiator
    attempted_at   = Column(DateTime, default=datetime.utcnow)


class KBItemValidationStatus(Base):
    """Per-item validation status for a given publish attempt.

    status values (from Goal 8 spec):
      approved     — usable in retrieval
      quarantined  — blocked from retrieval pending review
      needs_review — flagged; awaiting human decision
      rejected     — must be corrected before re-publish
    """
    __tablename__ = "kb_item_validation_status"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    kb_item_id         = Column(Integer, nullable=False, index=True)   # kb_articles.id
    publish_attempt_id = Column(Integer, nullable=True)                # kb_publish_attempts.id
    kb_version         = Column(Integer, nullable=False)
    status             = Column(String, nullable=False)                # approved|quarantined|needs_review|rejected
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KBValidationResult(Base):
    """One row per rule check for a KB item in a publish attempt.

    severity values: error | warning | info
      error   — causes quarantine/rejection
      warning — surfaced to reviewer but does not block alone
      info    — informational; no blocking effect
    """
    __tablename__ = "kb_validation_results"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    kb_item_id         = Column(Integer, nullable=False, index=True)   # kb_articles.id
    publish_attempt_id = Column(Integer, nullable=True)                # kb_publish_attempts.id
    kb_version         = Column(Integer, nullable=False)
    rule_id            = Column(String, nullable=False)                # stable rule identifier e.g. taxonomy.primary_required
    severity           = Column(String, nullable=False)                # error|warning|info
    message            = Column(Text, nullable=True)                   # human-readable description
    passed             = Column(Boolean, nullable=False)
    checked_at         = Column(DateTime, default=datetime.utcnow)


class KBReviewDecision(Base):
    """Human reviewer decision on a quarantined or needs_review KB item.

    decision values: approved | rejected | override
      approved — reviewer confirms item is safe to publish
      rejected — reviewer confirms item must be corrected
      override — reviewer bypasses a specific rule with explicit justification
    """
    __tablename__ = "kb_review_decisions"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    kb_item_id         = Column(Integer, nullable=False, index=True)   # kb_articles.id
    publish_attempt_id = Column(Integer, nullable=True)                # kb_publish_attempts.id
    kb_version         = Column(Integer, nullable=False)
    reviewer_id        = Column(String, nullable=False)                # username or user identifier
    decision           = Column(String, nullable=False)                # approved|rejected|override
    reason_code        = Column(String, nullable=True)                 # stable code e.g. content_correct|rule_false_positive|safety_risk
    notes              = Column(Text, nullable=True)                   # free-text reviewer notes
    decided_at         = Column(DateTime, default=datetime.utcnow)
