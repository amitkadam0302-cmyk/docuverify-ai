from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DocumentProcessingStatus, DocumentType, UploadedDocument, VerificationEventStatus
from app.services.explanation_service import generate_issue_explanations
from app.services.hash_service import verify_document_hash
from app.services.manual_review_service import ensure_manual_review
from app.services.metadata_service import analyze_document_metadata
from app.services.ocr_service import OCRUnavailableError, extract_document_text, extract_structured_fields
from app.services.qr_service import verify_qr_certificate
from app.services.resume_checker_service import check_resume_consistency
from app.services.scoring_service import classify_decision, classify_risk
from app.services.storage_service import resolve_local_path
from app.services.tamper_service import detect_document_tampering
from app.services.timeline_service import add_verification_event
from app.services.verification_result_service import get_or_create_verification_result, replace_fraud_flags


AGENT_PLANS = {
    DocumentType.CERTIFICATE: [
        "ocr",
        "qr_verification",
        "hash_verification",
        "metadata_analysis",
        "tamper_detection",
        "institution_match",
    ],
    DocumentType.RESUME: [
        "ocr",
        "metadata_analysis",
        "resume_consistency",
        "claim_extraction",
        "skill_verification",
    ],
    DocumentType.EXPERIENCE_LETTER: [
        "ocr",
        "metadata_analysis",
        "company_name_extraction",
        "date_consistency",
        "tamper_detection",
    ],
    DocumentType.MARKSHEET: [
        "ocr",
        "metadata_analysis",
        "tamper_detection",
        "institution_match",
        "marks_consistency",
    ],
    DocumentType.OTHER: [
        "ocr",
        "metadata_analysis",
        "tamper_detection",
    ],
}

ALL_CHECKS = sorted({check for checks in AGENT_PLANS.values() for check in checks})


def run_verification_agent(db: Session, document: UploadedDocument) -> dict[str, Any]:
    """Adaptive verification workflow used by the enterprise AI agent endpoint."""
    document_type = DocumentType(document.document_type)
    selected = AGENT_PLANS.get(document_type, AGENT_PLANS[DocumentType.OTHER])
    completed: list[str] = []
    skipped = [check for check in ALL_CHECKS if check not in selected]
    detailed: dict[str, Any] = {
        "agent": {"checks_selected": selected, "skipped_checks": skipped},
        "ocr": {"structured_fields": {}, "text_length": 0},
        "metadata": clean_metadata_default("skipped"),
        "qr": clean_qr_default("skipped"),
        "hash": clean_hash_default("skipped"),
        "tamper": clean_tamper_default("skipped"),
    }
    fraud_flags: list[dict[str, Any]] = []
    verification = get_or_create_verification_result(db, document_id=document.id)
    source_path = resolve_local_path(document.file_path)

    add_verification_event(
        db,
        document_id=document.id,
        event_type="agent_started",
        event_message=f"AI agent selected {len(selected)} checks for {document_type.value}.",
        status=VerificationEventStatus.COMPLETED,
    )

    extracted_text = ""
    fields: dict[str, Any] = {}
    if "ocr" in selected:
        ocr_warning = None
        try:
            extracted_text = extract_document_text(source_path)
        except OCRUnavailableError as exc:
            extracted_text = ""
            ocr_warning = str(exc)
        fields = extract_structured_fields(extracted_text)
        detailed["ocr"] = {
            "structured_fields": fields,
            "text_length": len(extracted_text),
            "status": "warning" if ocr_warning else "completed",
            "message": ocr_warning,
        }
        verification.extracted_text = extracted_text
        if extracted_text:
            completed.append("ocr")
        add_stage_event(db, document.id, "ocr", bool(extracted_text))

    if "metadata_analysis" in selected:
        metadata = analyze_document_metadata(source_path, fields.get("issue_date"))
        detailed["metadata"] = without_flags(metadata, "risk_flags")
        fraud_flags.extend(metadata.get("risk_flags", []))
        verification.metadata_status = metadata["metadata_status"]
        replace_fraud_flags(db, verification, "metadata_", metadata["risk_flags"])
        completed.append("metadata_analysis")
        add_stage_event(db, document.id, "metadata_analysis", metadata["metadata_status"] == "clean")

    if any(check in selected for check in {"qr_verification", "institution_match"}):
        qr = verify_qr_certificate(db, source_path, fields)
        detailed["qr"] = without_flags(qr, "fraud_flags")
        fraud_flags.extend(qr.get("fraud_flags", []))
        verification.qr_status = qr["qr_status"]
        verification.institution_match_status = str(qr.get("match_details", {}).get("institution_match"))
        replace_fraud_flags(db, verification, "qr_", qr["fraud_flags"])
        completed.append("qr_verification" if "qr_verification" in selected else "institution_match")
        if "institution_match" in selected and "institution_match" not in completed:
            completed.append("institution_match")
        add_stage_event(db, document.id, "qr_verification", qr["qr_status"] == "verified")

    if "hash_verification" in selected:
        certificate_id = detailed["qr"].get("certificate_id") or fields.get("certificate_id")
        hash_result = verify_document_hash(db, source_path, certificate_id)
        detailed["hash"] = without_flags(hash_result, "fraud_flags")
        fraud_flags.extend(hash_result.get("fraud_flags", []))
        verification.hash_status = hash_result["hash_status"]
        replace_fraud_flags(db, verification, "hash_", hash_result["fraud_flags"])
        completed.append("hash_verification")
        add_stage_event(db, document.id, "hash_verification", hash_result["hash_status"] == "matched")

    if "tamper_detection" in selected:
        tamper = detect_document_tampering(source_path)
        detailed["tamper"] = without_flags(tamper, "fraud_flags")
        if detailed["tamper"].get("heatmap_path"):
            detailed["tamper"]["heatmap_url"] = asset_url(detailed["tamper"]["heatmap_path"], "processed")
        fraud_flags.extend(tamper.get("fraud_flags", []))
        verification.tampering_status = tamper["tampering_status"]
        verification.heatmap_path = tamper.get("heatmap_path")
        replace_fraud_flags(db, verification, "tamper_", tamper["fraud_flags"])
        completed.append("tamper_detection")
        add_stage_event(db, document.id, "tamper_detection", tamper["tampering_status"] in {"clean", "low_signal"})

    specialized = run_specialized_checks(db, document, selected, extracted_text, fields)
    detailed["agent"]["specialized_checks"] = specialized
    completed.extend([item["check"] for item in specialized if item["status"] == "completed"])
    fraud_flags.extend([item["flag"] for item in specialized if item.get("flag")])

    score = score_agent_result(selected, detailed)
    risk_label, risk_level = classify_risk(score)
    final_decision = classify_decision(score)
    issue_summary = summarize_agent_issues(fraud_flags, selected, score)
    explanation_cards = generate_issue_explanations(fraud_flags)

    verification.authenticity_score = score
    verification.risk_level = risk_level
    verification.final_decision = final_decision
    verification.issue_summary = "\n".join(issue_summary)
    verification.detailed_results = {
        **detailed,
        "score": {
            "risk_label": risk_label,
            "component_scores": build_component_scores(selected, detailed),
            "explanation_cards": explanation_cards,
        },
    }
    verification.recommendation = recommendation_for_score(score, document_type.value)
    verification.ai_explanation = (
        f"The AI verification agent selected checks for a {document_type.value.replace('_', ' ')} "
        f"and produced a trust score of {score}/100."
    )
    document.processing_status = DocumentProcessingStatus.COMPLETED
    ensure_manual_review(db, verification)
    add_verification_event(
        db,
        document_id=document.id,
        event_type="agent_completed",
        event_message=f"AI agent completed verification with score {score}/100.",
        status=VerificationEventStatus.COMPLETED,
    )

    return {
        "document_id": document.id,
        "verification_id": verification.id,
        "detected_document_type": document_type.value,
        "checks_selected": selected,
        "checks_completed": dedupe(completed),
        "skipped_checks": skipped,
        "verification_summary": verification.ai_explanation,
        "final_score": score,
        "risk_level": risk_label,
        "recommendation": verification.recommendation,
        "authenticity_score": score,
        "final_decision": final_decision.value,
        "extracted_text": extracted_text,
        "fraud_flags": fraud_flags,
        "issue_summary": issue_summary,
        "detailed_results": verification.detailed_results,
        "explanation_cards": explanation_cards,
    }


def run_specialized_checks(
    db: Session,
    document: UploadedDocument,
    selected: list[str],
    text: str,
    fields: dict[str, Any],
) -> list[dict[str, Any]]:
    results = []
    if "resume_consistency" in selected:
        supporting_texts = candidate_supporting_texts(document)
        if supporting_texts:
            result = check_resume_consistency(text, supporting_texts)
            results.append({"check": "resume_consistency", "status": "completed", "score": result["consistency_score"], "details": result})
        else:
            results.append({"check": "resume_consistency", "status": "skipped", "score": 70, "reason": "No linked supporting documents."})
    if "claim_extraction" in selected:
        results.append({"check": "claim_extraction", "status": "completed", "score": 90 if fields else 55, "details": fields})
    if "skill_verification" in selected:
        skills = fields.get("skills") or []
        results.append({"check": "skill_verification", "status": "completed", "score": 85 if skills else 55, "details": {"skills_found": skills}})
    if "company_name_extraction" in selected:
        company = fields.get("company_name")
        results.append({"check": "company_name_extraction", "status": "completed", "score": 90 if company else 50, "details": {"company_name": company}})
    if "date_consistency" in selected:
        duration = fields.get("experience_duration")
        results.append({"check": "date_consistency", "status": "completed", "score": 85 if duration else 60, "details": {"experience_duration": duration}})
    if "marks_consistency" in selected:
        has_marks = any(token in text.lower() for token in ["marks", "grade", "cgpa", "percentage"])
        results.append({"check": "marks_consistency", "status": "completed", "score": 85 if has_marks else 60})
    return results


def candidate_supporting_texts(document: UploadedDocument) -> list[str]:
    texts = []
    for candidate_link in document.candidate_links:
        for linked in candidate_link.candidate.documents:
            if linked.document_id == document.id:
                continue
            verification = linked.document.verification_result
            if verification and verification.extracted_text:
                texts.append(verification.extracted_text)
    return texts


def score_agent_result(selected: list[str], detailed: dict[str, Any]) -> float:
    scores: list[float] = []
    component_scores = build_component_scores(selected, detailed)
    for check in selected:
        value = component_scores.get(check)
        if value is not None:
            scores.append(value)
    return round(sum(scores) / len(scores), 2) if scores else 0.0


def build_component_scores(selected: list[str], detailed: dict[str, Any]) -> dict[str, float]:
    specialized = {item["check"]: float(item.get("score") or 0) for item in detailed.get("agent", {}).get("specialized_checks", [])}
    return {
        "ocr": 100.0 if detailed.get("ocr", {}).get("text_length", 0) else 35.0,
        "metadata_analysis": max(0.0, 100.0 - float(detailed.get("metadata", {}).get("risk_score_component") or 0)),
        "qr_verification": 100.0 if detailed.get("qr", {}).get("qr_status") == "verified" else 35.0,
        "hash_verification": 100.0 if detailed.get("hash", {}).get("hash_match") else 40.0,
        "tamper_detection": max(0.0, 100.0 - float(detailed.get("tamper", {}).get("tamper_score") or 0)),
        "institution_match": 100.0 if detailed.get("qr", {}).get("database_match") else 50.0,
        "resume_consistency": specialized.get("resume_consistency", 70.0 if "resume_consistency" in selected else 0),
        "claim_extraction": specialized.get("claim_extraction", 0),
        "skill_verification": specialized.get("skill_verification", 0),
        "company_name_extraction": specialized.get("company_name_extraction", 0),
        "date_consistency": specialized.get("date_consistency", 0),
        "marks_consistency": specialized.get("marks_consistency", 0),
    }


def clean_metadata_default(status: str) -> dict[str, Any]:
    return {"metadata_summary": {}, "risk_flags": [], "metadata_status": status, "risk_score_component": 0}


def clean_qr_default(status: str) -> dict[str, Any]:
    return {"qr_found": False, "qr_value": None, "certificate_id": None, "database_match": False, "match_details": {}, "qr_status": status}


def clean_hash_default(status: str) -> dict[str, Any]:
    return {"uploaded_hash": None, "registered_hash": None, "hash_match": False, "hash_status": status, "explanation": ""}


def clean_tamper_default(status: str) -> dict[str, Any]:
    return {"tampering_status": status, "suspicious_regions": [], "tamper_score": 0, "heatmap_path": "", "explanation": ""}


def without_flags(result: dict[str, Any], flag_key: str) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != flag_key}


def summarize_agent_issues(flags: list[dict[str, Any]], selected: list[str], score: float) -> list[str]:
    if flags:
        return [flag["message"] for flag in flags[:8]]
    if score >= 75:
        return ["Agent checks completed without material fraud signals."]
    return ["Agent score requires recruiter review before acceptance."]


def recommendation_for_score(score: float, document_type: str) -> str:
    if score >= 90:
        return f"Accept this {document_type.replace('_', ' ')} with standard controls."
    if score >= 55:
        return "Send to manual review and verify high-impact claims."
    return "Do not approve until independent verification is complete."


def add_stage_event(db: Session, document_id: int, event_type: str, passed: bool) -> None:
    add_verification_event(
        db,
        document_id=document_id,
        event_type=event_type,
        event_message=f"{event_type.replace('_', ' ').title()} completed.",
        status=VerificationEventStatus.COMPLETED if passed else VerificationEventStatus.WARNING,
    )


def asset_url(file_path: str, mount_name: str) -> str:
    filename = file_path.replace("\\", "/").split("/")[-1]
    return f"{get_settings().public_base_url.rstrip('/')}/{mount_name}/{filename}"


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
