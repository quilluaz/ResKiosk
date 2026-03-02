from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, LargeBinary, ForeignKey, DateTime,
    Boolean
)
from hub.db.session import Base


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
    """Gold label when user selects a category after clarification."""
    __tablename__ = "clarification_resolutions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False)
    raw_transcript = Column(Text, nullable=True)
    resolved_intent = Column(String, nullable=False)
    language = Column(String, nullable=True)
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


class EvacInfo(Base):
    """Single-row table for all editable shelter operations data."""
    __tablename__ = "evac_info"

    id                 = Column(Integer, primary_key=True, default=1)
    food_schedule      = Column(Text)
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
    status         = Column(Text)  # 'pending', 'read', 'published', 'rejected'
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

    user_id  = Column(Integer, primary_key=True, autoincrement=True)
    fname    = Column(Text)
    mname    = Column(Text)
    lname    = Column(Text)
    password = Column(Text)  # Should be hashed



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
