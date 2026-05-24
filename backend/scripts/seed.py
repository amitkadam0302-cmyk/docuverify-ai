from datetime import date
from hashlib import sha256
import os
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, create_database_tables
from app.models import Certificate, CertificateStatus, Institution, User, UserRole
from app.services.ledger_service import create_ledger_entry
from app.utils.security import hash_password


def initialize_database_records(db: Session) -> None:
    settings = get_settings()
    institution = db.query(Institution).filter_by(code="MITACSC").one_or_none()
    if institution is None:
        institution = Institution(
            name="MIT Applied Sciences Institute",
            code="MITACSC",
            official_email="registrar@mitacsc.edu",
            website="https://mitacsc.edu",
            address="Alandi Road, Pune, Maharashtra",
            is_verified=True,
        )
        db.add(institution)
        db.flush()
    else:
        institution.name = "MIT Applied Sciences Institute"
        institution.official_email = "registrar@mitacsc.edu"
        institution.website = "https://mitacsc.edu"
        institution.address = "Alandi Road, Pune, Maharashtra"
        institution.is_verified = True

    users = [
        {
            "full_name": "Student User",
            "email": "student@example.com",
            "role": UserRole.STUDENT,
            "institution_id": None,
        },
        {
            "full_name": "Recruiter User",
            "email": "recruiter@example.com",
            "role": UserRole.RECRUITER,
            "institution_id": None,
        },
        {
            "full_name": "MITACSC Institution Admin",
            "email": "admin@mitacsc.edu",
            "role": UserRole.INSTITUTION_ADMIN,
            "institution_id": institution.id,
        },
        {
            "full_name": "Super Admin",
            "email": "superadmin@example.com",
            "role": UserRole.SUPER_ADMIN,
            "institution_id": None,
        },
    ]

    initial_password = os.getenv("INITIAL_USER_PASSWORD")
    for item in users:
        user = db.query(User).filter_by(email=item["email"]).one_or_none()
        if user is None and initial_password:
            db.add(
                User(
                    full_name=item["full_name"],
                    email=item["email"],
                    hashed_password=hash_password(initial_password),
                    role=item["role"],
                    institution_id=item["institution_id"],
                    is_active=True,
                    onboarding_completed=True,
                )
            )
        else:
            user.onboarding_completed = True

    certificates = [
        {
            "certificate_id": "MITACSC-CERT-2026-0001",
            "student_name": "Aarav Sharma",
            "course_name": "Bachelor of Computer Applications",
            "issue_date": date(2026, 4, 15),
        },
        {
            "certificate_id": "MITACSC-CERT-2026-0002",
            "student_name": "Maya Iyer",
            "course_name": "Master of Data Science",
            "issue_date": date(2026, 4, 20),
        },
    ]

    for item in certificates:
        exists = db.query(Certificate).filter_by(
            certificate_id=item["certificate_id"]
        ).one_or_none()
        certificate_hash = sha256(
            f"{item['certificate_id']}:{item['student_name']}:{institution.code}".encode()
        ).hexdigest()
        verification_url = f"{settings.public_base_url.rstrip('/')}/api/public/verify/{item['certificate_id']}"
        if exists is not None:
            exists.student_name = item["student_name"]
            exists.course_name = item["course_name"]
            exists.issue_date = item["issue_date"]
            exists.institution_id = institution.id
            exists.document_hash = certificate_hash
            exists.qr_code_value = verification_url
            continue

        certificate = Certificate(
            **item,
            institution_id=institution.id,
            document_hash=certificate_hash,
            qr_code_value=verification_url,
            status=CertificateStatus.VALID,
        )
        db.add(certificate)
        db.flush()
        create_ledger_entry(
            db,
            certificate_id=certificate.certificate_id,
            action="certificate_initialized",
            payload_hash=certificate.document_hash,
        )

    db.commit()


if __name__ == "__main__":
    create_database_tables()
    with SessionLocal() as session:
        initialize_database_records(session)
    print("Initial records are ready.")
