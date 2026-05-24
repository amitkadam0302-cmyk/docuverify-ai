from enum import StrEnum


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum values instead of Python member names in the database."""
    return [member.value for member in enum_class]


class UserRole(StrEnum):
    STUDENT = "student"
    RECRUITER = "recruiter"
    INSTITUTION_ADMIN = "institution_admin"
    COMPANY_ADMIN = "company_admin"
    SUPER_ADMIN = "super_admin"


class CertificateStatus(StrEnum):
    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class DocumentType(StrEnum):
    CERTIFICATE = "certificate"
    RESUME = "resume"
    EXPERIENCE_LETTER = "experience_letter"
    MARKSHEET = "marksheet"
    OTHER = "other"


class DocumentProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class FinalDecision(StrEnum):
    VERIFIED = "verified"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    LIKELY_FRAUD = "likely_fraud"
    REJECTED = "rejected"
    AUTHENTIC = "authentic"
    SUSPICIOUS = "suspicious"
    FRAUDULENT = "fraudulent"
    REVIEW_REQUIRED = "review_required"


class FraudSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ManualReviewStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MORE_INFO_REQUIRED = "more_info_required"


class ManualReviewPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationEventStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    WARNING = "warning"
    FAILED = "failed"


class BatchVerificationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(StrEnum):
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    MEMBER = "member"


class WorkspaceMemberStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"
