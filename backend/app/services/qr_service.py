import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np
from sqlalchemy.orm import Session

from app.models import Certificate, CertificateStatus
from app.services.ocr_service import find_certificate_id
from app.services.storage_service import resolve_local_path


def extract_qr_value(file_path: str | Path) -> str | None:
    path = Path(resolve_local_path(str(file_path)))
    if path.suffix.lower() == ".pdf":
        return read_pdf_qr(path)
    return read_qr_with_opencv(path)


def read_pdf_qr(file_path: str | Path) -> str | None:
    with fitz.open(file_path) as document:
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, 3
            )
            value = detect_qr_from_array(image)
            if value:
                return value
    return None


def read_qr_with_opencv(file_path: str | Path) -> str | None:
    image = cv2.imread(str(file_path))
    if image is None:
        return None
    return detect_qr_from_array(image)


def detect_qr_from_array(image: np.ndarray) -> str | None:
    detector = cv2.QRCodeDetector()
    value, _, _ = detector.detectAndDecode(image)
    return value or None


def extract_certificate_id_from_qr(qr_value: str | None) -> str | None:
    if not qr_value:
        return None
    direct = find_certificate_id(qr_value)
    if direct:
        return direct
    match = re.search(r"(?:verify|certificate|cert)[/=:_-]+([A-Z0-9][A-Z0-9/-]{4,})", qr_value, re.I)
    if match:
        return match.group(1).strip().upper()
    return None


def verify_qr_certificate(
    db: Session,
    file_path: str | Path,
    ocr_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ocr_fields = ocr_fields or {}
    qr_value = extract_qr_value(file_path)
    qr_certificate_id = extract_certificate_id_from_qr(qr_value)
    certificate_id = qr_certificate_id or ocr_fields.get("certificate_id")

    flags: list[dict[str, Any]] = []
    match_details: dict[str, Any] = {
        "certificate_exists": False,
        "status_valid": False,
        "student_name_match": None,
        "institution_match": None,
        "qr_value_match": None,
    }

    if not qr_value:
        flags.append(
            {
                "flag_type": "qr_not_found",
                "severity": "medium",
                "message": "No QR code could be detected in the uploaded document.",
            }
        )

    if not certificate_id:
        flags.append(
            {
                "flag_type": "qr_certificate_id_not_found",
                "severity": "high",
                "message": "No certificate ID was found in QR data or OCR text.",
            }
        )
        return build_qr_response(False, qr_value, None, False, match_details, flags)

    certificate = db.query(Certificate).filter_by(certificate_id=certificate_id).one_or_none()
    if certificate is None:
        flags.append(
            {
                "flag_type": "qr_certificate_not_found",
                "severity": "high",
                "message": "Certificate ID was not found in trusted institution records.",
            }
        )
        return build_qr_response(bool(qr_value), qr_value, certificate_id, False, match_details, flags)

    match_details["certificate_exists"] = True
    match_details["status_valid"] = certificate.status == CertificateStatus.VALID

    if certificate.status == CertificateStatus.REVOKED:
        flags.append(
            {
                "flag_type": "qr_certificate_revoked",
                "severity": "critical",
                "message": "Certificate record exists but has been revoked.",
            }
        )
    elif certificate.status != CertificateStatus.VALID:
        flags.append(
            {
                "flag_type": "qr_certificate_not_valid",
                "severity": "high",
                "message": f"Certificate status is {certificate.status.value}.",
            }
        )

    candidate_name = ocr_fields.get("candidate_name")
    if candidate_name:
        name_score = similarity(candidate_name, certificate.student_name)
        match_details["student_name_match"] = {
            "ocr_value": candidate_name,
            "record_value": certificate.student_name,
            "score": name_score,
            "matched": name_score >= 0.78,
        }
        if name_score < 0.78:
            flags.append(
                {
                    "flag_type": "qr_candidate_name_mismatch",
                    "severity": "high",
                    "message": "Candidate name from OCR does not match the certificate record.",
                }
            )

    institution_name = ocr_fields.get("institution_name")
    if institution_name and certificate.institution:
        institution_score = similarity(institution_name, certificate.institution.name)
        match_details["institution_match"] = {
            "ocr_value": institution_name,
            "record_value": certificate.institution.name,
            "score": institution_score,
            "matched": institution_score >= 0.72,
        }
        if institution_score < 0.72:
            flags.append(
                {
                    "flag_type": "qr_institution_mismatch",
                    "severity": "high",
                    "message": "Institution name from OCR does not match the trusted record.",
                }
            )

    if qr_value and certificate.qr_code_value:
        qr_matches = normalize(qr_value) == normalize(certificate.qr_code_value)
        match_details["qr_value_match"] = {
            "uploaded_value": qr_value,
            "record_value": certificate.qr_code_value,
            "matched": qr_matches,
        }
        if not qr_matches:
            flags.append(
                {
                    "flag_type": "qr_value_mismatch",
                    "severity": "medium",
                    "message": "QR value does not match the value stored for this certificate.",
                }
            )

    database_match = match_details["certificate_exists"] and match_details["status_valid"]
    qr_status = "verified" if database_match and not flags else "suspicious"
    if any(flag["severity"] == "critical" for flag in flags):
        qr_status = "rejected"

    return build_qr_response(
        bool(qr_value),
        qr_value,
        certificate_id,
        database_match,
        match_details,
        flags,
        qr_status=qr_status,
    )


def build_qr_response(
    qr_found: bool,
    qr_value: str | None,
    certificate_id: str | None,
    database_match: bool,
    match_details: dict[str, Any],
    flags: list[dict[str, Any]],
    qr_status: str = "failed",
) -> dict[str, Any]:
    return {
        "qr_found": qr_found,
        "qr_value": qr_value,
        "certificate_id": certificate_id,
        "database_match": database_match,
        "match_details": match_details,
        "qr_status": qr_status,
        "fraud_flags": flags,
    }


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())
