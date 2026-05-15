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
    authority: Optional[str] = None  # official|shelter_staff|volunteer|unknown
    scope: Optional[str] = None      # shelter_local|general
    center_id: Optional[str] = None
    hub_id: Optional[str] = None

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
    authority: Optional[str] = None
    scope: Optional[str] = None
    center_id: Optional[str] = None
    hub_id: Optional[str] = None


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
    authority: Optional[str] = None
    scope: Optional[str] = None
    center_id: Optional[str] = None
    hub_id: Optional[str] = None

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
    """A single taxonomy-backed clarification chip.

    Each chip has a stable ID (from the taxonomy DAG) and a human-readable
    display label.  The kiosk renders these as tappable buttons; when the
    user selects one, the ID is sent back via `selected_taxonomy_node_id`
    in the retry request.
    """
    id: str      # stable taxonomy node ID (e.g. "rk.tax.health_medical.medical_services")
    label: str   # human-readable display label (e.g. "Medical Services")


class ClarificationContext(BaseModel):
    """Context included when the pipeline is paused for clarification.

    Provides all fields the kiosk needs to display clarification options
    and resume the query after the user selects a category.
    """
    original_query: str                        # raw query text (pre-normalization)
    normalized_text: str                       # post-normalization text
    detected_intent: str                       # intent classifier result
    intent_confidence: float                   # intent classifier confidence
    suggested_categories: List[str]            # legacy category chips (backward compat)
    clarification_options: Optional[List[TaxonomyOption]] = None  # taxonomy-backed chips
    kb_version: int                            # KB version at time of pause
    session_id: Optional[str] = None           # session for resumption
    pipeline_status: str = "paused"            # always "paused" for clarification


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


class TaxonomyOption(BaseModel):
    id: str
    label: str


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
    # Clarification pause context — populated only when answer_type == NEEDS_CLARIFICATION
    clarification_context: Optional[ClarificationContext] = None


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


# ─── Goal 8 / Slice 3 Story 2 — Metadata validation storage ─────────────────

class KBPublishAttemptResponse(BaseModel):
    id: int
    kb_version: int
    status: str                        # pass|blocked|partial
    total_items: Optional[int] = None
    approved_count: Optional[int] = None
    quarantined_count: Optional[int] = None
    rejected_count: Optional[int] = None
    attempted_by: Optional[str] = None
    attempted_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KBItemValidationStatusResponse(BaseModel):
    id: int
    kb_item_id: int
    publish_attempt_id: Optional[int] = None
    kb_version: int
    status: str                        # approved|quarantined|needs_review|rejected
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KBValidationResultResponse(BaseModel):
    id: int
    kb_item_id: int
    publish_attempt_id: Optional[int] = None
    kb_version: int
    rule_id: str
    severity: str                      # error|warning|info
    message: Optional[str] = None
    passed: bool
    checked_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KBReviewDecisionCreate(BaseModel):
    """Payload for a human reviewer submitting a decision."""
    kb_item_id: int
    publish_attempt_id: Optional[int] = None
    kb_version: int
    decision: str                      # approved|rejected|override
    reason_code: Optional[str] = None  # content_correct|rule_false_positive|safety_risk|…
    notes: Optional[str] = None


class KBReviewDecisionResponse(BaseModel):
    id: int
    kb_item_id: int
    publish_attempt_id: Optional[int] = None
    kb_version: int
    reviewer_id: str
    decision: str
    reason_code: Optional[str] = None
    notes: Optional[str] = None
    decided_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Goal 8 / Slice 3 Story 4 — Metadata review queue (admin API) ────────────


class MetadataRuleResultPublic(BaseModel):
    rule_id: str
    severity: str
    passed: bool
    message: str


class MetadataReviewQueueItem(BaseModel):
    kb_item_id: int
    live_status: str
    kb_version: int
    latest_db_status: Optional[str] = None
    failed_rules: List[MetadataRuleResultPublic] = Field(default_factory=list)


class MetadataReviewQueueResponse(BaseModel):
    items: List[MetadataReviewQueueItem]
    kb_version: int


class MetadataArticleSnapshot(BaseModel):
    id: int
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    enabled: bool = True
    authority: Optional[str] = None
    scope: Optional[str] = None
    status: Optional[str] = None


class MetadataValidationArticleDetail(BaseModel):
    kb_item_id: int
    kb_version: int
    article: MetadataArticleSnapshot
    live_status: str
    live_rule_results: List[MetadataRuleResultPublic] = Field(default_factory=list)
    persisted_validation_results: List[Dict[str, Any]] = Field(default_factory=list)
    review_decisions: List[Dict[str, Any]] = Field(default_factory=list)


class MetadataReviewApplyResponse(BaseModel):
    status: str = "ok"
    kb_item_id: int
    validation_status_after: str
    review_decision_id: int


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
