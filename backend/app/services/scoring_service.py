from typing import Any

from app.models import FinalDecision, RiskLevel

WEIGHTS = {
    "institution_record_match": 25,
    "hash_verification": 20,
    "qr_certificate_validation": 15,
    "ocr_consistency": 15,
    "tampering_detection": 15,
    "metadata_analysis": 10,
}


def calculate_authenticity_score(results: dict[str, Any]) -> dict[str, Any]:
    components = {
        "institution_record_match": component(bool(results["qr"].get("database_match"))),
        "hash_verification": component(bool(results["hash"].get("hash_match"))),
        "qr_certificate_validation": component(results["qr"].get("qr_status") == "verified"),
        "ocr_consistency": component(ocr_is_consistent(results["qr"].get("match_details", {}))),
        "tampering_detection": tamper_component(results["tamper"].get("tamper_score", 0)),
        "metadata_analysis": metadata_component(results["metadata"].get("risk_score_component", 0)),
    }
    score = sum(components[key] * WEIGHTS[key] / 100 for key in WEIGHTS)
    risk_label, risk_level = classify_risk(score)
    final_decision = classify_decision(score)
    issue_summary = summarize_issues(results)
    recommendation = build_recommendation(score, issue_summary)
    return {
        "authenticity_score": round(score, 2),
        "risk_level": risk_level,
        "risk_label": risk_label,
        "final_decision": final_decision,
        "issue_summary": issue_summary,
        "component_scores": components,
        "recommendation": recommendation,
        "ai_explanation": build_professional_explanation(score, risk_label, issue_summary),
    }


def component(passed: bool) -> float:
    return 100.0 if passed else 0.0


def ocr_is_consistent(match_details: dict[str, Any]) -> bool:
    checked = [
        value.get("matched")
        for value in (
            match_details.get("student_name_match"),
            match_details.get("institution_match"),
        )
        if isinstance(value, dict)
    ]
    return all(checked) if checked else bool(match_details.get("certificate_exists"))


def tamper_component(tamper_score: float) -> float:
    return max(0.0, 100.0 - float(tamper_score))


def metadata_component(risk_score: float) -> float:
    return max(0.0, 100.0 - float(risk_score))


def classify_risk(score: float) -> tuple[str, RiskLevel]:
    if score >= 90:
        return "Very Low Risk", RiskLevel.VERY_LOW
    if score >= 75:
        return "Low Risk", RiskLevel.LOW
    if score >= 55:
        return "Medium Risk", RiskLevel.MEDIUM
    if score >= 35:
        return "High Risk", RiskLevel.HIGH
    return "Very High Risk", RiskLevel.VERY_HIGH


def classify_decision(score: float) -> FinalDecision:
    if score >= 90:
        return FinalDecision.VERIFIED
    if score >= 55:
        return FinalDecision.MANUAL_REVIEW_REQUIRED
    if score >= 35:
        return FinalDecision.LIKELY_FRAUD
    return FinalDecision.REJECTED


def summarize_issues(results: dict[str, Any]) -> list[str]:
    issues = []
    for key in ("qr", "hash", "tamper"):
        for flag in results[key].get("fraud_flags", []):
            issues.append(flag["message"])
    for flag in results["metadata"].get("risk_flags", []):
        issues.append(flag["message"])
    if not issues:
        issues.append("No material authenticity issues were detected by automated checks.")
    return issues


def build_recommendation(score: float, issues: list[str]) -> str:
    if score >= 90:
        return "Document can be treated as verified, subject to normal business controls."
    if score >= 55:
        return "Route to manual review and confirm key claims with the issuing institution."
    return "Do not accept this document until independent verification is completed."


def build_professional_explanation(score: float, risk_label: str, issues: list[str]) -> str:
    return (
        f"The document received an authenticity score of {score:.2f}/100 ({risk_label}). "
        f"The assessment combines institution record matching, hash verification, QR validation, "
        f"OCR consistency, tampering signals, and metadata forensics. Key finding: {issues[0]}"
    )
