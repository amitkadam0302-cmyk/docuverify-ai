from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_institution_admin
from app.models import Certificate, Institution, User, UserRole
from app.schemas.certificates import (
    CertificateIssueRequest,
    CertificateIssueResponse,
    CertificateResponse,
    VerificationLedgerResponse,
)
from app.services.certificate_service import issue_certificate_record
from app.config import get_settings

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post(
    "/issue",
    response_model=CertificateIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_certificate(
    payload: CertificateIssueRequest,
    current_user: User = Depends(require_institution_admin),
    db: Session = Depends(get_db),
) -> CertificateIssueResponse:
    institution_id = payload.institution_id
    if current_user.role != UserRole.SUPER_ADMIN:
        institution_id = current_user.institution_id

    if institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An institution is required to issue a certificate.",
        )

    institution = db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )

    existing_certificate = (
        db.query(Certificate)
        .filter_by(certificate_id=payload.certificate_id)
        .one_or_none()
    )
    if existing_certificate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A certificate with this ID already exists.",
        )

    issued = issue_certificate_record(
        db=db,
        institution=institution,
        certificate_id=payload.certificate_id,
        student_name=payload.student_name,
        course_name=payload.course_name,
        issue_date=payload.issue_date,
        status=payload.status,
        document_hash=payload.document_hash,
        qr_code_value=payload.qr_code_value,
    )
    db.commit()
    db.refresh(issued.certificate)
    return CertificateIssueResponse(
        **CertificateResponse.model_validate(issued.certificate).model_dump(),
        verification_url=issued.verification_url,
        qr_image_path=issued.qr_image_path,
        qr_image_url=asset_url(issued.qr_image_path, "generated_qr"),
        ledger_entry=VerificationLedgerResponse.model_validate(issued.ledger_entry),
    )


@router.get("/{certificate_id}/ledger", response_model=list[VerificationLedgerResponse])
def get_certificate_ledger(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> list:
    certificate = db.query(Certificate).filter_by(certificate_id=certificate_id).one_or_none()
    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )
    return certificate.ledger_entries


def asset_url(file_path: str, mount_name: str) -> str:
    settings = get_settings()
    filename = file_path.replace("\\", "/").split("/")[-1]
    return f"{settings.public_base_url.rstrip('/')}/{mount_name}/{filename}"
