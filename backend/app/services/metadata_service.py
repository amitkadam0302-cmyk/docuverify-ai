from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from PIL import ExifTags, Image
from pypdf import PdfReader

from app.services.ocr_service import parse_date_value
from app.services.storage_service import resolve_local_path

SUSPICIOUS_SOFTWARE_KEYWORDS = {
    "photoshop",
    "canva",
    "illustrator",
    "acrobat",
    "pdf editor",
    "smallpdf",
    "ilovepdf",
    "sejda",
    "online editor",
    "gimp",
    "figma",
}


def analyze_document_metadata(
    file_path: str | Path,
    claimed_issue_date: str | None = None,
) -> dict[str, Any]:
    """Run metadata forensics for a document.

    Metadata is not proof by itself, but it is valuable forensic context. A file that
    claims to be an old certificate yet was created yesterday in an image editor should
    receive more scrutiny than a document with consistent creation software and dates.
    """
    path = Path(resolve_local_path(str(file_path)))
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".pdf":
        summary = analyze_pdf_metadata(path)
    else:
        summary = analyze_image_metadata(path)

    risk_flags = detect_metadata_risks(summary, claimed_issue_date=claimed_issue_date)
    risk_score = min(100.0, sum(float(flag["score"]) for flag in risk_flags))
    metadata_status = "suspicious" if risk_score >= 50 else "warning" if risk_score else "clean"

    return {
        "metadata_summary": summary,
        "risk_flags": risk_flags,
        "metadata_status": metadata_status,
        "risk_score_component": risk_score,
    }


def analyze_pdf_metadata(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    summary: dict[str, Any] = {
        "filename": path.name,
        "file_type": "pdf",
        "dimensions": None,
        "creation_date": None,
        "modification_date": None,
        "author": None,
        "producer": None,
        "creator_software": None,
        "image_device_info": None,
        "raw": {},
    }

    with fitz.open(path) as document:
        first_page = document[0] if document.page_count else None
        summary["dimensions"] = (
            {"width": first_page.rect.width, "height": first_page.rect.height}
            if first_page
            else None
        )
        pymupdf_metadata = document.metadata or {}
        summary["raw"]["pymupdf"] = pymupdf_metadata
        summary["creation_date"] = normalize_pdf_date(pymupdf_metadata.get("creationDate"))
        summary["modification_date"] = normalize_pdf_date(pymupdf_metadata.get("modDate"))
        summary["author"] = pymupdf_metadata.get("author")
        summary["producer"] = pymupdf_metadata.get("producer")
        summary["creator_software"] = pymupdf_metadata.get("creator")

    reader = PdfReader(str(path))
    pypdf_metadata = dict(reader.metadata or {})
    summary["raw"]["pypdf"] = {str(key): str(value) for key, value in pypdf_metadata.items()}

    summary["creation_date"] = summary["creation_date"] or normalize_pdf_date(
        pypdf_metadata.get("/CreationDate")
    )
    summary["modification_date"] = summary["modification_date"] or normalize_pdf_date(
        pypdf_metadata.get("/ModDate")
    )
    summary["author"] = summary["author"] or clean_metadata_value(pypdf_metadata.get("/Author"))
    summary["producer"] = summary["producer"] or clean_metadata_value(
        pypdf_metadata.get("/Producer")
    )
    summary["creator_software"] = summary["creator_software"] or clean_metadata_value(
        pypdf_metadata.get("/Creator")
    )
    return summary


def extract_pdf_metadata(file_path: str | Path) -> dict[str, Any]:
    return analyze_pdf_metadata(file_path)


def analyze_image_metadata(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    with Image.open(path) as image:
        exif = image.getexif()
        readable_exif = {
            ExifTags.TAGS.get(tag_id, str(tag_id)): value
            for tag_id, value in exif.items()
        }
        software = clean_metadata_value(readable_exif.get("Software"))
        device_info = {
            "make": clean_metadata_value(readable_exif.get("Make")),
            "model": clean_metadata_value(readable_exif.get("Model")),
            "software": software,
        }
        return {
            "filename": path.name,
            "file_type": (image.format or path.suffix.lstrip(".")).lower(),
            "dimensions": {"width": image.width, "height": image.height},
            "creation_date": normalize_exif_date(
                readable_exif.get("DateTimeOriginal") or readable_exif.get("DateTime")
            ),
            "modification_date": normalize_exif_date(readable_exif.get("DateTimeDigitized")),
            "author": clean_metadata_value(readable_exif.get("Artist")),
            "producer": None,
            "creator_software": software,
            "image_device_info": device_info,
            "raw": {"exif": stringify_values(readable_exif)},
        }


def extract_image_metadata(file_path: str | Path) -> dict[str, Any]:
    return analyze_image_metadata(file_path)


def detect_metadata_risks(
    summary: dict[str, Any],
    claimed_issue_date: str | None,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    software_text = " ".join(
        str(summary.get(key) or "")
        for key in ("creator_software", "producer")
    ).lower()

    for keyword in SUSPICIOUS_SOFTWARE_KEYWORDS:
        if keyword in software_text:
            flags.append(
                {
                    "flag_type": "metadata_suspicious_software",
                    "severity": "high",
                    "message": f"Metadata references editing software: {keyword}.",
                    "score": 35.0,
                }
            )
            break

    created_at = parse_metadata_datetime(summary.get("creation_date"))
    modified_at = parse_metadata_datetime(summary.get("modification_date"))
    issue_date = parse_date_value(claimed_issue_date)

    if issue_date and modified_at and modified_at.date() > issue_date.date():
        flags.append(
            {
                "flag_type": "metadata_modified_after_issue_date",
                "severity": "high",
                "message": "File metadata indicates modification after the claimed issue date.",
                "score": 35.0,
            }
        )

    if issue_date and created_at and created_at.date() > issue_date.date():
        flags.append(
            {
                "flag_type": "metadata_created_after_issue_date",
                "severity": "medium",
                "message": "File creation date is later than the claimed document issue date.",
                "score": 25.0,
            }
        )

    if issue_date and created_at:
        age_gap_days = (datetime.now(timezone.utc).date() - issue_date.date()).days
        creation_age_days = (datetime.now(timezone.utc).date() - created_at.date()).days
        if age_gap_days > 365 and creation_age_days <= 30:
            flags.append(
                {
                    "flag_type": "metadata_recent_file_old_claim",
                    "severity": "medium",
                    "message": "Document claims an older issue date but the file was created recently.",
                    "score": 20.0,
                }
            )

    missing_core_metadata = not any(
        summary.get(field)
        for field in ("creation_date", "modification_date", "creator_software", "producer")
    )
    if missing_core_metadata:
        flags.append(
            {
                "flag_type": "metadata_missing_core_fields",
                "severity": "low",
                "message": "Core metadata fields are missing; this can happen after editing or export.",
                "score": 10.0,
            }
        )

    return flags


def normalize_pdf_date(value: Any) -> str | None:
    cleaned = clean_metadata_value(value)
    if not cleaned:
        return None
    cleaned = cleaned.removeprefix("D:")
    match = cleaned[:14]
    try:
        return datetime.strptime(match, "%Y%m%d%H%M%S").isoformat()
    except ValueError:
        return cleaned


def normalize_exif_date(value: Any) -> str | None:
    cleaned = clean_metadata_value(value)
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%Y:%m:%d %H:%M:%S").isoformat()
    except ValueError:
        return cleaned


def parse_metadata_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def clean_metadata_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def stringify_values(values: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in values.items()}
