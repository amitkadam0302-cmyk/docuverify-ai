from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import Certificate
from app.services.hashing_service import calculate_sha256

HASH_EXPLANATION = (
    "If the uploaded document is exactly the same as the issued document, hash will "
    "match. If any content changed, hash will fail."
)


def verify_document_hash(
    db: Session,
    file_path: str | Path,
    certificate_id: str | None,
) -> dict[str, Any]:
    uploaded_hash = calculate_sha256(file_path)
    registered_hash = None
    hash_match = False
    flags: list[dict[str, Any]] = []

    if certificate_id:
        certificate = db.query(Certificate).filter_by(certificate_id=certificate_id).one_or_none()
        if certificate is not None:
            registered_hash = certificate.document_hash
            hash_match = uploaded_hash == certificate.document_hash

    if certificate_id and registered_hash is None:
        hash_status = "certificate_not_found"
        flags.append(
            {
                "flag_type": "hash_certificate_not_found",
                "severity": "high",
                "message": "Hash check could not find a trusted certificate record.",
            }
        )
    elif registered_hash is None:
        hash_status = "not_available"
        flags.append(
            {
                "flag_type": "hash_certificate_id_missing",
                "severity": "medium",
                "message": "Hash check requires a certificate ID to compare against the trusted hash.",
            }
        )
    elif hash_match:
        hash_status = "matched"
    else:
        hash_status = "mismatch"
        flags.append(
            {
                "flag_type": "hash_mismatch",
                "severity": "high",
                "message": "Uploaded document hash does not match the trusted issued-document hash.",
            }
        )

    return {
        "uploaded_hash": uploaded_hash,
        "registered_hash": registered_hash,
        "hash_match": hash_match,
        "hash_status": hash_status,
        "explanation": HASH_EXPLANATION,
        "fraud_flags": flags,
    }

