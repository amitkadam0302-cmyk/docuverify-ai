from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    BatchVerificationStatus,
    DocumentProcessingStatus,
    DocumentType,
    ManualReviewPriority,
    ManualReviewStatus,
    NotificationType,
    VerificationEventStatus,
    WorkspaceMemberStatus,
    WorkspaceRole,
)


class ManualReviewCreateRequest(BaseModel):
    document_id: int
    verification_id: int | None = None
    assigned_to: int | None = None
    priority: ManualReviewPriority = ManualReviewPriority.MEDIUM


class ManualReviewStatusUpdateRequest(BaseModel):
    status: ManualReviewStatus
    reviewer_comment: str | None = None


class ManualReviewAssignRequest(BaseModel):
    assigned_to: int | None = None
    priority: ManualReviewPriority | None = None


class ManualReviewDecisionRequest(BaseModel):
    status: ManualReviewStatus
    final_decision: str | None = None
    reviewer_comment: str | None = None


class ManualReviewCommentRequest(BaseModel):
    reviewer_comment: str


class ManualReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    verification_id: int | None
    assigned_to: int | None
    status: ManualReviewStatus
    priority: ManualReviewPriority
    reviewer_comment: str | None
    final_decision: str | None = None
    created_at: datetime
    updated_at: datetime
    document: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    fraud_flags: list[dict[str, Any]] = []


class VerificationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    event_type: str
    event_message: str
    status: VerificationEventStatus
    created_at: datetime


class BatchUploadResponse(BaseModel):
    batch_id: int
    batch_name: str
    total_documents: int
    completed_count: int
    status: BatchVerificationStatus
    documents: list[dict[str, Any]]


class BatchCreateRequest(BaseModel):
    batch_name: str = Field(..., min_length=2)


class BatchResultResponse(BaseModel):
    batch_id: int
    batch_name: str
    total_documents: int
    completed_count: int
    completed_documents: int = 0
    failed_documents: int = 0
    status: BatchVerificationStatus
    results: list[dict[str, Any]]


class CandidateCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: str | None = None
    phone: str | None = None
    document_ids: list[int] = []


class CandidateLinkDocumentsRequest(BaseModel):
    document_ids: list[int]


class CandidateProfileResponse(BaseModel):
    candidate_id: int
    full_name: str
    email: str | None
    phone: str | None
    uploaded_documents: list[dict[str, Any]]
    overall_trust_score: float
    mismatch_summary: list[str]
    final_recommendation: str
    verified_education: list[str] = []
    verified_certificates: list[str] = []
    verified_experience: list[str] = []


class TrustPassportCreateRequest(BaseModel):
    candidate_id: int


class TrustPassportResponse(BaseModel):
    id: int
    candidate_id: int
    public_slug: str
    public_token: str | None = None
    public_url: str
    qr_image_url: str | None
    overall_score: float = 0
    education_score: float = 0
    certificate_score: float = 0
    experience_score: float = 0
    resume_score: float = 0
    risk_level: str = "very_high"
    candidate: CandidateProfileResponse


class DocumentComparisonRequest(BaseModel):
    left_document_id: int
    right_document_id: int


class DocumentComparisonResponse(BaseModel):
    similarity_score: float
    mismatches: list[dict[str, Any]]
    left_fields: dict[str, Any]
    right_fields: dict[str, Any]
    left_text: str
    right_text: str


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    ip_address: str | None
    created_at: datetime
    user_email: str | None = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime


class SettingsProfileRequest(BaseModel):
    full_name: str | None = None
    notification_preference: bool | None = None
    theme_preference: str | None = None


class ResearchMetricsResponse(BaseModel):
    ocr_accuracy: list[dict[str, Any]]
    tamper_detection: list[dict[str, Any]]
    verification_rates: list[dict[str, Any]]
    confusion_matrix: list[dict[str, Any]]
    explanations: list[dict[str, str]]
    qr_verification: dict[str, float] = {}
    hash_verification: dict[str, float] = {}
    overall_fraud_detection: dict[str, float] = {}
    risk_distribution: list[dict[str, Any]] = []
    verification_volume: list[dict[str, Any]] = []


class AgentVerifyResponse(BaseModel):
    document_id: int
    verification_id: int
    detected_document_type: str
    checks_selected: list[str]
    checks_completed: list[str]
    skipped_checks: list[str]
    verification_summary: str
    final_score: float
    risk_level: str
    recommendation: str
    authenticity_score: float
    final_decision: str
    extracted_text: str | None = None
    fraud_flags: list[dict[str, Any]] = []
    issue_summary: list[str] = []
    detailed_results: dict[str, Any] = {}
    explanation_cards: list[dict[str, Any]] = []


class SystemSettingsResponse(BaseModel):
    settings: dict[str, Any]


class SystemSettingsUpdateRequest(BaseModel):
    settings: dict[str, Any]


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    plan: str = "starter"


class WorkspaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    plan: str | None = None


class WorkspaceInviteRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberRoleRequest(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int | None
    role: WorkspaceRole
    status: WorkspaceMemberStatus
    created_at: datetime
    user_email: str | None = None
    full_name: str | None = None


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int | None
    plan: str
    created_at: datetime
    updated_at: datetime
    members: list[WorkspaceMemberResponse] = []
