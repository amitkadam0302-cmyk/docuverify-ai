from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path

import qrcode
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Certificate, CertificateStatus, Institution, VerificationLedger
from app.services.ledger_service import create_ledger_entry


@dataclass(frozen=True)
class IssuedCertificate:
    certificate: Certificate
    verification_url: str
    qr_image_path: str
    ledger_entry: VerificationLedger


def build_certificate_hash(
    certificate_id: str,
    student_name: str,
    course_name: str,
    issue_date: date,
    institution_code: str,
) -> str:
    fingerprint = (
        f"{certificate_id}:{student_name}:{course_name}:{issue_date.isoformat()}:"
        f"{institution_code}"
    )
    return sha256(fingerprint.encode()).hexdigest()


def build_verification_url(certificate_id: str) -> str:
    settings = get_settings()
    return f"{settings.frontend_url.rstrip('/')}/verify/{certificate_id}"


def generate_certificate_qr(certificate_id: str, qr_value: str) -> str:
    settings = get_settings()
    directory = Path(settings.generated_qr_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{certificate_id}.png"
    image = qrcode.make(qr_value)
    image.save(path)
    return str(path)


def issue_certificate_record(
    db: Session,
    institution: Institution,
    certificate_id: str,
    student_name: str,
    course_name: str,
    issue_date: date,
    status: CertificateStatus = CertificateStatus.VALID,
    document_hash: str | None = None,
    qr_code_value: str | None = None,
) -> IssuedCertificate:
    verification_url = qr_code_value or build_verification_url(certificate_id)
    resolved_hash = document_hash or build_certificate_hash(
        certificate_id=certificate_id,
        student_name=student_name,
        course_name=course_name,
        issue_date=issue_date,
        institution_code=institution.code,
    )
    qr_path = generate_certificate_qr(certificate_id, verification_url)

    certificate = Certificate(
        certificate_id=certificate_id,
        student_name=student_name,
        course_name=course_name,
        issue_date=issue_date,
        institution_id=institution.id,
        document_hash=resolved_hash,
        qr_code_value=verification_url,
        status=status,
    )
    db.add(certificate)
    db.flush()
    ledger_entry = create_ledger_entry(
        db,
        certificate_id=certificate.certificate_id,
        action="certificate_issued",
        payload_hash=certificate.document_hash,
    )
    return IssuedCertificate(
        certificate=certificate,
        verification_url=verification_url,
        qr_image_path=qr_path,
        ledger_entry=ledger_entry,
    )
