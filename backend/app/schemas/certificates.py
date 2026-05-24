from datetime import date, datetime
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from app.models import CertificateStatus


class CertificateIssueRequest(BaseModel):
    certificate_id: str = Field(..., min_length=4, max_length=128)
    student_name: str = Field(..., min_length=2, max_length=255)
    course_name: str = Field(..., min_length=2, max_length=255)
    issue_date: date
    institution_id: int | None = None
    document_hash: str | None = Field(default=None, min_length=64, max_length=64)
    qr_code_value: str | None = Field(default=None, max_length=512)
    status: CertificateStatus = CertificateStatus.VALID

    def resolved_hash(self, institution_code: str) -> str:
        if self.document_hash:
            return self.document_hash.lower()
        fingerprint = f"{self.certificate_id}:{self.student_name}:{institution_code}"
        return sha256(fingerprint.encode()).hexdigest()


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    certificate_id: str
    student_name: str
    course_name: str
    issue_date: date
    institution_id: int
    document_hash: str
    qr_code_value: str | None
    status: CertificateStatus
    created_at: datetime


class VerificationLedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    certificate_id: str
    previous_hash: str | None
    current_hash: str
    timestamp: datetime
    action: str


class CertificateIssueResponse(CertificateResponse):
    verification_url: str
    qr_image_path: str
    qr_image_url: str
    ledger_entry: VerificationLedgerResponse


class PublicCertificateVerification(BaseModel):
    certificate_id: str
    certificate_status: CertificateStatus
    student_name: str
    institution_name: str
    course_name: str
    issue_date: date
    revoked_or_valid: str
    is_valid: bool
    qr_code_value: str | None = None
    verification_url: str | None = None
