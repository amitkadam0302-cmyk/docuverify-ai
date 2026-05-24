import re
from datetime import datetime
from typing import Any

from app.services.ocr_service import find_skills


def check_resume_consistency(
    resume_text: str,
    supporting_texts: list[str],
) -> dict[str, Any]:
    resume_skills = set(find_skills(resume_text))
    supporting_combined = "\n".join(supporting_texts)
    supporting_skills = set(find_skills(supporting_combined))
    mismatches: list[dict[str, Any]] = []

    for skill in sorted(supporting_skills - resume_skills):
        mismatches.append(
            mismatch(
                "certificate_skill_not_found_in_resume",
                "medium",
                f"Supporting document references '{skill}', but the resume does not.",
            )
        )

    for skill in sorted(resume_skills - supporting_skills):
        mismatches.append(
            mismatch(
                "resume_skill_without_supporting_certificate",
                "low",
                f"Resume lists '{skill}' without supporting certificate evidence.",
            )
        )

    resume_jobs = extract_job_entries(resume_text)
    for left, right in find_overlaps(resume_jobs):
        mismatches.append(
            mismatch(
                "overlapping_job_dates",
                "high",
                f"Job dates overlap between {left['company']} and {right['company']}.",
            )
        )

    supporting_companies = extract_companies(supporting_combined)
    resume_companies = extract_companies(resume_text)
    for company in supporting_companies - resume_companies:
        mismatches.append(
            mismatch(
                "company_name_mismatch",
                "medium",
                f"Experience letter company '{company}' was not found in resume employment history.",
            )
        )

    supporting_designations = extract_designations(supporting_combined)
    resume_designations = extract_designations(resume_text)
    for designation in supporting_designations - resume_designations:
        mismatches.append(
            mismatch(
                "designation_mismatch",
                "medium",
                f"Supporting document designation '{designation}' was not found in resume text.",
            )
        )

    education_dates = extract_years(resume_text)
    if len(education_dates) >= 2 and any(year > datetime.now().year + 1 for year in education_dates):
        mismatches.append(
            mismatch("impossible_timeline", "high", "Resume contains a future timeline that appears impossible.")
        )

    consistency_score = max(0.0, 100.0 - sum(severity_penalty(item["severity"]) for item in mismatches))
    recommendation = (
        "Proceed with standard recruiter review."
        if consistency_score >= 80
        else "Request clarification and manually verify supporting documents."
        if consistency_score >= 55
        else "Treat profile as high-risk until claims are independently verified."
    )
    return {
        "consistency_score": round(consistency_score, 2),
        "mismatches": mismatches,
        "explanation": "Rule-based HR consistency checks compared resume claims with supporting documents.",
        "recommendation": recommendation,
    }


def llm_ready_resume_prompt(resume_text: str, supporting_texts: list[str]) -> str:
    return (
        "Review this resume and supporting document text for HR verification inconsistencies. "
        "Return JSON with mismatches, severity, and recommendation.\n\n"
        f"RESUME:\n{resume_text}\n\nSUPPORTING DOCUMENTS:\n{chr(10).join(supporting_texts)}"
    )


def mismatch(kind: str, severity: str, message: str) -> dict[str, Any]:
    return {"flag_type": f"resume_{kind}", "severity": severity, "message": message}


def severity_penalty(severity: str) -> float:
    return {"low": 6.0, "medium": 12.0, "high": 22.0, "critical": 35.0}.get(severity, 10.0)


def extract_companies(text: str) -> set[str]:
    patterns = [r"(?:company|employer)\s*[:\-]\s*([^\n\r]+)", r"\bat\s+([A-Z][A-Za-z0-9 &.]{2,})"]
    return extract_labeled_set(text, patterns)


def extract_designations(text: str) -> set[str]:
    patterns = [r"(?:designation|position|job title|role)\s*[:\-]\s*([^\n\r]+)"]
    return extract_labeled_set(text, patterns)


def extract_labeled_set(text: str, patterns: list[str]) -> set[str]:
    values = set()
    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = re.sub(r"\s+", " ", match).strip(" .:-")
            if 2 <= len(cleaned) <= 80:
                values.add(cleaned)
    return values


def extract_job_entries(text: str) -> list[dict[str, Any]]:
    entries = []
    for line in text.splitlines():
        years = extract_years(line)
        if len(years) >= 2:
            entries.append(
                {
                    "company": next(iter(extract_companies(line)), "Unknown employer"),
                    "start": min(years),
                    "end": max(years),
                }
            )
    return entries


def find_overlaps(entries: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    overlaps = []
    for index, left in enumerate(entries):
        for right in entries[index + 1 :]:
            if left["start"] <= right["end"] and right["start"] <= left["end"]:
                overlaps.append((left, right))
    return overlaps


def extract_years(text: str) -> list[int]:
    return [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", text)]
