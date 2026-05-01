from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, field_validator, Field
import json


class NetworkInfo(BaseModel):
    ip: str
    port: int


# ─── KB Articles ─────────────────────────────────────────────────────────────

class ArticleBase(BaseModel):
    question: str
    answer: str
    category: str
    tags: List[str] = []
    enabled: bool = True
    status: Optional[str] = "draft"

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        """Accept both JSON lists and comma-separated strings."""
        if isinstance(v, str):
            # Try JSON array first (legacy), then comma-split
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return [t.strip() for t in v.split(",") if t.strip()]
        return v or []


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None
    status: Optional[str] = None


class ArticleResponse(BaseModel):
    id: int
    question: str
    answer: str
    category: Optional[str] = None
    tags: List[str] = []
    enabled: bool = True
    source: Optional[str] = None
    created_at: Optional[int] = None
    last_updated: Optional[int] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator('question', mode='before')
    @classmethod
    def coerce_question(cls, v, info):
        return v or ""

    @field_validator('answer', mode='before')
    @classmethod
    def coerce_answer(cls, v, info):
        return v or ""

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return [t.strip() for t in v.split(",") if t.strip()]
        return v or []

    @field_validator('enabled', mode='before')
    @classmethod
    def coerce_enabled(cls, v):
        """DB stores enabled as 0/1 int; coerce to bool."""
        return bool(v)


# ─── KB Snapshot / Version ────────────────────────────────────────────────────

class KBSnapshot(BaseModel):
    kb_version: int
    articles: List[ArticleResponse]
    structured_config: "EvacInfoResponse"   # Use structured model instead of Any dict


class KBVersionResponse(BaseModel):
    kb_version: int
    updated_at: Optional[int] = None    # maps to SystemVersion.last_published


# ─── Query ───────────────────────────────────────────────────────────────────

class TaxonomyOption(BaseModel):
    id: str
    label: str


class QueryRequest(BaseModel):
    center_id: str
    kiosk_id: str
    transcript_original: str
    transcript_english: Optional[str] = None
    language: str
    kb_version: int
    is_retry: bool = False
    selected_category: Optional[str] = None
    selected_taxonomy_node_id: Optional[str] = None
    session_id: Optional[str] = None
    # Optional list of KB article IDs that should be excluded from consideration
    exclude_source_ids: Optional[List[int]] = None
    stt_mode: Optional[str] = None   # cloud|local (reported by kiosk)
    tts_mode: Optional[str] = None   # cloud|local (reported by kiosk)
    cloud_consent_mode: Optional[str] = None  # operator|session|disabled
    follow_up_token: Optional[str] = None



class QueryResponse(BaseModel):
    answer_text_en: str
    answer_text_localized: Optional[str] = None
    answer_type: str
    confidence: float
    kb_version: int
    source_id: Optional[int] = None
    clarification_categories: Optional[List[str]] = None
    clarification_options: Optional[List[TaxonomyOption]] = None
    # ID of the QueryLog row corresponding to this response (for RLHF feedback)
    query_log_id: Optional[int] = None
    # Shadow RLHF fields: what the RLHF ranker would pick as top, if enabled
    rlhf_top_source_id: Optional[int] = None
    rlhf_top_score: Optional[float] = None
    follow_up_prompt: Optional[str] = None
    follow_up_intent: Optional[str] = None


# ─── Evac Info ───────────────────────────────────────────────────────────────

class EvacInfoResponse(BaseModel):
    id: int
    food_schedule: Optional[str] = None
    food_distribution_location: Optional[str] = None
    sleeping_zones: Optional[str] = None
    medical_station: Optional[str] = None
    registration_steps: Optional[str] = None
    announcements: Optional[str] = None
    emergency_mode: Optional[str] = None
    last_updated: Optional[str] = None
    metadata: Optional[str] = Field(None, alias="info_metadata", serialization_alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EvacSyncSummary(BaseModel):
    changed_count: int = 0
    changed_ids: List[int] = []
    disabled_count: int = 0
    embedded_count: int = 0


class EvacInfoUpdateResponse(EvacInfoResponse):
    kb_version: Optional[int] = None
    published_at: Optional[int] = None
    evac_sync: Optional[EvacSyncSummary] = None


class EvacFreshnessSection(BaseModel):
    section: str
    last_reviewed_at: Optional[int] = None
    reviewed_by: Optional[str] = None
    age_days: Optional[int] = None
    expires_at: Optional[int] = None
    is_expired: bool


class EvacFreshnessResponse(BaseModel):
    freshness_days: int
    sections: List[EvacFreshnessSection]
    expired_sections: List[str] = []


class EvacFreshnessConfirmRequest(BaseModel):
    sections: List[str]
    note: Optional[str] = None


# ─── Emergency ───────────────────────────────────────────────────────────────

# ─── Evac Info ───────────────────────────────────────────────────────────────

class EvacInfoResponse(BaseModel):
    id: int
    food_schedule: Optional[str] = None
    food_distribution_location: Optional[str] = None
    sleeping_zones: Optional[str] = None
    medical_station: Optional[str] = None
    registration_steps: Optional[str] = None
    announcements: Optional[str] = None
    emergency_mode: Optional[str] = None
    last_updated: Optional[str] = None
    metadata: Optional[str] = Field(None, alias="info_metadata", serialization_alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ─── Emergency ───────────────────────────────────────────────────────────────

class EmergencyRequest(BaseModel):
    kiosk_id: str
    kiosk_location: str
    hub_id: Optional[str] = None
    transcript: Optional[str] = None
    language: str = "en"
    timestamp: Optional[int] = None
    tier: Optional[int] = 1
    alert_id_local: Optional[str] = None
    retry_count: Optional[int] = 0


class EmergencyResolveRequest(BaseModel):
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None


class EmergencyModeUpdateRequest(BaseModel):
    active: bool


class EmergencyModeResponse(BaseModel):
    active: bool
    activated_at: int = 0


class EmergencyStatusResponse(BaseModel):
    id: int
    status: str
    acknowledged_at: Optional[int] = None
    responding_at: Optional[int] = None
    dismissed_at: Optional[int] = None
    dismissed_by_kiosk: Optional[int] = None
    resolved_at: Optional[int] = None


class FeedbackRequest(BaseModel):
    """Feedback signal from kiosk for RLHF-style ranking."""
    session_id: Optional[str] = None
    query_log_id: int
    source_id: Optional[int] = None
    label: int  # -1=inaccurate (v1), +1=thumbs-up (future v2)
    language: str
    kiosk_id: Optional[str] = None
    center_id: Optional[str] = None


# ─── Structured Config ────────────────────────────────────────────────────────

class StructuredConfigUpsert(BaseModel):
    value: Any


class StructuredConfigResponse(BaseModel):
    key: str
    value: Any
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
# ─── Hub Messaging ───────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    category_id: Optional[int] = None
    target_hub_id: Optional[int] = None   # None = broadcast
    subject: str
    content: str
    priority: str = "normal"              # 'normal', 'urgent', 'emergency'

class MessageUpdate(BaseModel):
    status: Optional[str] = None          # 'pending', 'read', 'published', 'rejected'

class MessageResponse(BaseModel):
    id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    source_hub_id: Optional[int] = None
    source_hub_name: Optional[str] = None
    target_hub_id: Optional[int] = None
    target_hub_name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    sent_at: Optional[int] = None
    received_at: Optional[int] = None
    published_at: Optional[int] = None
    location: Optional[str] = None
    created_by: Optional[str] = None
    hop_count: Optional[int] = None
    ttl: Optional[int] = None
    received_via: Optional[str] = None
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CategoryResponse(BaseModel):
    category_id: int
    category_name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class HubResponse(BaseModel):
    hub_id: int
    hub_name: str
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FAQTrackerItem(BaseModel):
    id: int
    source_id: int
    source_question: Optional[str] = None
    source_answer: Optional[str] = None
    question_normalized: Optional[str] = None
    question_display: Optional[str] = None
    language: Optional[str] = None
    count: int
    first_asked_at: Optional[int] = None
    last_asked_at: Optional[int] = None
    kiosk_id: Optional[str] = None
    answer_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FaqSuggestionItem(BaseModel):
    source_id: int
    question: str
    count: int

    model_config = ConfigDict(from_attributes=True)


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    username: str
    fname: Optional[str] = None
    lname: Optional[str] = None
    is_first_login: bool


class ProfileSetupRequest(BaseModel):
    first_name: str
    last_name: str
    new_password: str


class UserResponse(BaseModel):
    user_id: int
    username: str
    fname: Optional[str] = None
    lname: Optional[str] = None
    is_first_login: bool

    model_config = ConfigDict(from_attributes=True)
