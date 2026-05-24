import re
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from app.services.storage_service import resolve_local_path

OCR_FALLBACK_MESSAGE = "OCR engine not available. Install Tesseract and configure path."

SKILL_KEYWORDS = {
    "aws",
    "azure",
    "docker",
    "excel",
    "fastapi",
    "git",
    "java",
    "javascript",
    "kubernetes",
    "machine learning",
    "node",
    "opencv",
    "postgresql",
    "python",
    "react",
    "sql",
    "tensorflow",
}


class OCRUnavailableError(RuntimeError):
    """Raised when the configured OCR engine or native binary is unavailable."""


def extract_document_text(file_path: str | Path, engine: str = "tesseract") -> str:
    """Extract text from a PDF or image.

    PDFs are handled in two passes: first native text extraction through PyMuPDF,
    then page rendering plus OCR for scanned documents that contain no text layer.
    The `engine` argument keeps the public API easy to swap to EasyOCR later.
    """
    path = Path(resolve_local_path(str(file_path)))
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path, engine=engine)
    return extract_image_text(path, engine=engine)


def extract_pdf_text(file_path: str | Path, engine: str = "tesseract") -> str:
    path = Path(file_path)
    with fitz.open(path) as document:
        text = "\n".join(page.get_text("text").strip() for page in document).strip()
        if text:
            return normalize_text(text)

        page_text: list[str] = []
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            page_text.append(extract_text_from_image_object(image, engine=engine))
        return normalize_text("\n".join(page_text))


def extract_image_text(file_path: str | Path, engine: str = "tesseract") -> str:
    path = Path(file_path)
    with Image.open(path) as image:
        return normalize_text(extract_text_from_image_object(image, engine=engine))


def extract_text_from_image_object(image: Image.Image, engine: str = "tesseract") -> str:
    if engine == "tesseract":
        try:
            import pytesseract
            from pytesseract import TesseractNotFoundError
        except ImportError as exc:
            raise OCRUnavailableError(OCR_FALLBACK_MESSAGE) from exc

        try:
            return pytesseract.image_to_string(image)
        except (TesseractNotFoundError, RuntimeError) as exc:
            raise OCRUnavailableError(OCR_FALLBACK_MESSAGE) from exc

    if engine == "easyocr":
        try:
            import numpy as np
            import easyocr
        except ImportError as exc:
            raise OCRUnavailableError("EasyOCR engine is not installed.") from exc

        reader = easyocr.Reader(["en"], gpu=False)
        results = reader.readtext(np.array(image.convert("RGB")), detail=0)
        return "\n".join(results)

    raise ValueError(f"Unsupported OCR engine: {engine}")


def extract_structured_fields(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    fields: dict[str, Any] = {
        "candidate_name": find_labeled_value(
            normalized, ["candidate name", "student name", "name"]
        ),
        "institution_name": find_labeled_value(
            normalized, ["institution", "university", "institute"]
        ),
        "course_name": find_labeled_value(
            normalized, ["course", "program", "degree", "qualification"]
        ),
        "issue_date": find_date(normalized),
        "certificate_id": find_certificate_id(normalized),
        "company_name": find_labeled_value(normalized, ["company", "employer"]),
        "designation": find_labeled_value(
            normalized, ["designation", "position", "job title", "role"]
        ),
        "experience_duration": find_experience_duration(normalized),
        "skills": find_skills(normalized),
        "emails": sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", normalized))),
        "phone_numbers": sorted(
            set(re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", normalized))
        ),
    }
    return fields


def normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def find_labeled_value(text: str, labels: list[str]) -> str | None:
    label_expression = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_expression})\s*[:\-]\s*([^\n\r]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" .:-")
    return None


def find_certificate_id(text: str) -> str | None:
    patterns = [
        r"(?:certificate|cert\.?|registration|serial)\s*(?:id|no|number)?\s*[:#-]\s*([A-Z0-9][A-Z0-9/-]{4,})",
        r"\b([A-Z]{2,10}[-/][A-Z0-9]{2,10}[-/][A-Z0-9-]{3,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
    return None


def find_date(text: str) -> str | None:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def find_experience_duration(text: str) -> str | None:
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?|months?)\b",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else None


def find_skills(text: str) -> list[str]:
    lower_text = text.lower()
    return sorted(skill for skill in SKILL_KEYWORDS if skill in lower_text)


def parse_date_value(value: str | None) -> datetime | None:
    if not value:
        return None
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y"]
    for date_format in formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue
    return None
