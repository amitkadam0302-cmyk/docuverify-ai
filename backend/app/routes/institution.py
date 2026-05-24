from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.dependencies import require_institution_admin
from app.models import Certificate, CertificateStatus, Institution, NotificationType, User, UserRole
from app.schemas.certificates import (
    CertificateIssueRequest,
    CertificateIssueResponse,
    CertificateResponse,
    VerificationLedgerResponse,
)
from app.services.certificate_service import issue_certificate_record
from app.services.audit_service import log_action
from app.services.ledger_service import create_ledger_entry
from app.services.notification_service import create_notification

router = APIRouter(prefix="/institution", tags=["institution"])


def resolve_admin_institution(
    db: Session,
    current_user: User,
    requested_institution_id: int | None,
) -> Institution:
    institution_id = requested_institution_id
    if current_user.role != UserRole.SUPER_ADMIN:
        institution_id = current_user.institution_id
    if institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Institution context is required.",
        )
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    return institution


@router.post(
    "/certificates/issue",
    response_model=CertificateIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_institution_certificate(
    payload: CertificateIssueRequest,
    request: Request,
    current_user: User = Depends(require_institution_admin),
    db: Session = Depends(get_db),
) -> CertificateIssueResponse:
    institution = resolve_admin_institution(db, current_user, payload.institution_id)
    existing = db.query(Certificate).filter_by(certificate_id=payload.certificate_id).one_or_none()
    if existing is not None:
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
    log_action(
        db,
        user=current_user,
        action="certificate_issued",
        entity_type="certificate",
        entity_id=issued.certificate.certificate_id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=current_user.id,
        title="Certificate issued",
        message=f"{issued.certificate.certificate_id} issued.",
        type=NotificationType.SUCCESS,
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


@router.get("/certificates", response_model=list[CertificateResponse])
def list_institution_certificates(
    current_user: User = Depends(require_institution_admin),
    db: Session = Depends(get_db),
) -> list[Certificate]:
    query = db.query(Certificate)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter_by(institution_id=current_user.institution_id)
    return query.order_by(Certificate.created_at.desc()).all()


@router.patch("/certificates/{id}/revoke", response_model=CertificateResponse)
def revoke_certificate(
    id: int,
    request: Request,
    current_user: User = Depends(require_institution_admin),
    db: Session = Depends(get_db),
) -> Certificate:
    certificate = db.get(Certificate, id)
    if certificate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found.")
    if (
        current_user.role != UserRole.SUPER_ADMIN
        and certificate.institution_id != current_user.institution_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke certificates for another institution.",
        )
    certificate.status = CertificateStatus.REVOKED
    create_ledger_entry(
        db,
        certificate_id=certificate.certificate_id,
        action="certificate_revoked",
        payload_hash=certificate.document_hash,
    )
    log_action(
        db,
        user=current_user,
        action="certificate_revoked",
        entity_type="certificate",
        entity_id=certificate.certificate_id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=current_user.id,
        title="Certificate revoked",
        message=f"{certificate.certificate_id} revoked.",
        type=NotificationType.WARNING,
    )
    db.commit()
    db.refresh(certificate)
    return certificate


def asset_url(file_path: str, mount_name: str) -> str:
    settings = get_settings()
    filename = file_path.replace("\\", "/").split("/")[-1]
    return f"{settings.public_base_url.rstrip('/')}/{mount_name}/{filename}"
