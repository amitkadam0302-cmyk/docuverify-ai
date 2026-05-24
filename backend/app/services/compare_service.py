from typing import Any

from app.services.ocr_service import extract_document_text, extract_structured_fields


FIELDS_TO_COMPARE = [
    "candidate_name",
    "institution_name",
    "company_name",
    "certificate_id",
    "course_name",
    "issue_date",
    "designation",
    "experience_duration",
]


def compare_documents(left_path: str, right_path: str) -> dict[str, Any]:
    left_text = extract_document_text(left_path)
    right_text = extract_document_text(right_path)
    left_fields = extract_structured_fields(left_text)
    right_fields = extract_structured_fields(right_text)
    mismatches = []
    matches = 0
    comparable = 0

    for field in FIELDS_TO_COMPARE:
        left_value = normalize(left_fields.get(field))
        right_value = normalize(right_fields.get(field))
        if not left_value and not right_value:
            continue
        comparable += 1
        matched = bool(left_value and right_value and left_value == right_value)
        if matched:
            matches += 1
        else:
            mismatches.append(
                {
                    "field": field,
                    "left_value": left_fields.get(field),
                    "right_value": right_fields.get(field),
                    "message": f"{field.replace('_', ' ').title()} differs between the two documents.",
                }
            )

    text_similarity = token_similarity(left_text, right_text)
    field_similarity = (matches / comparable * 100) if comparable else 100.0
    similarity_score = round((field_similarity * 0.65) + (text_similarity * 0.35), 2)
    return {
        "similarity_score": similarity_score,
        "mismatches": mismatches,
        "left_fields": left_fields,
        "right_fields": right_fields,
        "left_text": left_text[:2500],
        "right_text": right_text[:2500],
    }


def normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def token_similarity(left_text: str, right_text: str) -> float:
    left_tokens = set(normalize(left_text).split())
    right_tokens = set(normalize(right_text).split())
    if not left_tokens and not right_tokens:
        return 100.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) * 100
