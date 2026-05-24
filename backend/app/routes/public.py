from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models import Certificate, CertificateStatus, TrustPassport
from app.schemas.certificates import PublicCertificateVerification
from app.schemas.workflows import TrustPassportResponse, CandidateProfileResponse
from app.routes.candidates import serialize_passport
from app.services.audit_service import log_action

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/verify/{certificate_id}", response_model=PublicCertificateVerification)
def public_verify_certificate(
    certificate_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicCertificateVerification:
    certificate = db.query(Certificate).filter_by(certificate_id=certificate_id).one_or_none()
    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )
    log_action(
        db,
        user=None,
        action="public_verification_accessed",
        entity_type="certificate",
        entity_id=certificate.certificate_id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return PublicCertificateVerification(
        certificate_id=certificate.certificate_id,
        certificate_status=certificate.status,
        student_name=certificate.student_name,
        institution_name=certificate.institution.name,
        course_name=certificate.course_name,
        issue_date=certificate.issue_date,
        revoked_or_valid=(
            "valid" if certificate.status == CertificateStatus.VALID else "revoked_or_invalid"
        ),
        is_valid=certificate.status == CertificateStatus.VALID,
        qr_code_value=certificate.qr_code_value,
        verification_url=f"{get_settings().frontend_url.rstrip('/')}/verify/{certificate.certificate_id}",
    )


@router.get("/passports/{slug}", response_model=TrustPassportResponse)
@router.get("/passport/{slug}", response_model=TrustPassportResponse)
def public_verify_trust_passport(
    slug: str,
    db: Session = Depends(get_db),
) -> TrustPassportResponse:
    passport = (
        db.query(TrustPassport)
        .filter(
            TrustPassport.is_public.is_(True),
            (TrustPassport.public_slug == slug) | (TrustPassport.public_token == slug),
        )
        .one_or_none()
    )
    if passport is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trust Passport not found.",
        )
    return serialize_passport(passport)
