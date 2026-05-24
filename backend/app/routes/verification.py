from pathlib import Path

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, is_admin, require_recruiter_or_admin
from app.models import (
    DocumentProcessingStatus,
    NotificationType,
    UploadedDocument,
    User,
    UserRole,
    VerificationEventStatus,
    VerificationResult,
)
from app.schemas.verification import (
    FullCheckResponse,
    HashVerifyResponse,
    MetadataResponse,
    OCRResponse,
    QRVerifyResponse,
    ResumeConsistencyRequest,
    ResumeConsistencyResponse,
    TamperDetectResponse,
)
from app.services.hash_service import verify_document_hash
from app.services.audit_service import log_action
from app.services.explanation_service import generate_issue_explanations
from app.services.metadata_service import analyze_document_metadata
from app.services.manual_review_service import ensure_manual_review
from app.services.notification_service import create_notification
from app.services.ocr_service import (
    OCRUnavailableError,
    extract_document_text,
    extract_structured_fields,
)
from app.services.qr_service import (
    extract_certificate_id_from_qr,
    extract_qr_value,
    verify_qr_certificate,
)
from app.services.resume_checker_service import check_resume_consistency
from app.services.report_service import generate_verification_report
from app.services.scoring_service import calculate_authenticity_score
from app.services.storage_service import resolve_local_path
from app.services.tamper_service import detect_document_tampering
from app.services.timeline_service import add_verification_event
from app.services.verification_result_service import (
    get_or_create_verification_result,
    replace_fraud_flags,
)

router = APIRouter(prefix="/verification", tags=["verification"])


def get_uploaded_document_or_404(db: Session, document_id: int) -> UploadedDocument:
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document


def get_document_text(document: UploadedDocument) -> str:
    return document.verification_result.extracted_text if document.verification_result else ""


def ensure_verification_access(document: UploadedDocument, current_user: User) -> None:
    if document.uploaded_by == current_user.id or current_user.role == UserRole.RECRUITER or is_admin(current_user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this verification.",
    )


def document_processing_path(document: UploadedDocument) -> str:
    return resolve_local_path(document.file_path)


@router.post("/{document_id}/ocr", response_model=OCRResponse)
def run_ocr(
    document_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> OCRResponse:
    document = get_uploaded_document_or_404(db, document_id)

    try:
        source_path = document_processing_path(document)
        extracted_text = extract_document_text(source_path)
    except OCRUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored document file was not found.",
        ) from exc

    structured_fields = extract_structured_fields(extracted_text)
    verification = get_or_create_verification_result(db, document_id=document.id)
    verification.extracted_text = extracted_text
    verification.ai_explanation = "OCR text extraction completed."
    document.processing_status = DocumentProcessingStatus.COMPLETED
    db.commit()

    return OCRResponse(
        document_id=document.id,
        extracted_text=extracted_text,
        structured_fields=structured_fields,
    )


@router.post("/{document_id}/qr-verify", response_model=QRVerifyResponse)
def run_qr_verify(
    document_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> QRVerifyResponse:
    document = get_uploaded_document_or_404(db, document_id)
    verification = get_or_create_verification_result(db, document_id=document.id)
    fields = extract_structured_fields(verification.extracted_text or "")
    result = verify_qr_certificate(db, document_processing_path(document), fields)
    verification.qr_status = result["qr_status"]
    verification.institution_match_status = str(
        result["match_details"].get("institution_match")
    )
    replace_fraud_flags(db, verification, "qr_", result["fraud_flags"])
    db.commit()
    return QRVerifyResponse(**without_internal_flags(result))


@router.post("/{document_id}/hash-verify", response_model=HashVerifyResponse)
def run_hash_verify(
    document_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> HashVerifyResponse:
    document = get_uploaded_document_or_404(db, document_id)
    verification = get_or_create_verification_result(db, document_id=document.id)
    fields = extract_structured_fields(verification.extracted_text or "")
    certificate_id = fields.get("certificate_id")
    if not certificate_id:
        certificate_id = extract_certificate_id_from_qr(extract_qr_value(document_processing_path(document)))
    result = verify_document_hash(db, document_processing_path(document), certificate_id)
    verification.hash_status = result["hash_status"]
    replace_fraud_flags(db, verification, "hash_", result["fraud_flags"])
    db.commit()
    return HashVerifyResponse(**without_internal_flags(result))


@router.post("/{document_id}/metadata", response_model=MetadataResponse)
def run_metadata_analysis(
    document_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    document = get_uploaded_document_or_404(db, document_id)
    verification = get_or_create_verification_result(db, document_id=document.id)

    structured_fields = extract_structured_fields(verification.extracted_text or "")
    try:
        analysis = analyze_document_metadata(
            file_path=document_processing_path(document),
            claimed_issue_date=structured_fields.get("issue_date"),
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored document file was not found.",
        ) from exc

    verification.metadata_status = analysis["metadata_status"]
    verification.ai_explanation = "Metadata forensic analysis completed."

    replace_fraud_flags(db, verification, "metadata_", analysis["risk_flags"])

    db.commit()

    return MetadataResponse(
        document_id=document.id,
        metadata_summary=analysis["metadata_summary"],
        risk_flags=analysis["risk_flags"],
        metadata_status=analysis["metadata_status"],
        risk_score_component=analysis["risk_score_component"],
    )


@router.post("/{document_id}/tamper-detect", response_model=TamperDetectResponse)
def run_tamper_detection(
    document_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> TamperDetectResponse:
    document = get_uploaded_document_or_404(db, document_id)
    verification = get_or_create_verification_result(db, document_id=document.id)
    try:
        result = detect_document_tampering(document_processing_path(document))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored document file was not found.",
        ) from exc
    verification.tampering_status = result["tampering_status"]
    replace_fraud_flags(db, verification, "tamper_", result["fraud_flags"])
    db.commit()
    return TamperDetectResponse(**without_internal_flags(result))


@router.post("/resume-consistency", response_model=ResumeConsistencyResponse)
def run_resume_consistency(
    payload: ResumeConsistencyRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ResumeConsistencyResponse:
    resume_document = get_uploaded_document_or_404(db, payload.resume_document_id)
    resume_text = get_document_text(resume_document)
    if not resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume OCR text is not available. Run OCR first.",
        )

    supporting_texts = []
    for document_id in payload.supporting_document_ids:
        document = get_uploaded_document_or_404(db, document_id)
        text = get_document_text(document)
        if text:
            supporting_texts.append(text)

    result = check_resume_consistency(resume_text, supporting_texts)
    verification = get_or_create_verification_result(db, resume_document.id)
    replace_fraud_flags(db, verification, "resume_", result["mismatches"])
    db.commit()
    return ResumeConsistencyResponse(**result)


@router.post("/{document_id}/full-check", response_model=FullCheckResponse)
def run_full_check(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullCheckResponse:
    document = get_uploaded_document_or_404(db, document_id)
    ensure_verification_access(document, current_user)
    verification = get_or_create_verification_result(db, document_id=document.id)
    log_action(
        db,
        user=current_user,
        action="verification_started",
        entity_type="uploaded_document",
        entity_id=document.id,
        ip_address=request.client.host if request.client else None,
    )
    add_verification_event(
        db,
        document_id=document.id,
        event_type="upload_received",
        event_message="Uploaded document was received by the verification pipeline.",
        status=VerificationEventStatus.COMPLETED,
    )

    ocr_warning: str | None = None
    try:
        source_path = document_processing_path(document)
        extracted_text = extract_document_text(source_path)
    except OCRUnavailableError as exc:
        extracted_text = ""
        ocr_warning = str(exc)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored document file was not found.",
        ) from exc

    fields = extract_structured_fields(extracted_text)
    verification.extracted_text = extracted_text
    add_verification_event(
        db,
        document_id=document.id,
        event_type="ocr_extraction",
        event_message=ocr_warning or f"OCR extraction completed with {len(extracted_text)} characters extracted.",
        status=VerificationEventStatus.COMPLETED if extracted_text else VerificationEventStatus.WARNING,
    )

    metadata = analyze_document_metadata(source_path, fields.get("issue_date"))
    add_verification_event(
        db,
        document_id=document.id,
        event_type="metadata_forensics",
        event_message=f"Metadata analysis completed with status {metadata['metadata_status']}.",
        status=VerificationEventStatus.WARNING if metadata["metadata_status"] != "clean" else VerificationEventStatus.COMPLETED,
    )
    qr = verify_qr_certificate(db, source_path, fields)
    add_verification_event(
        db,
        document_id=document.id,
        event_type="qr_validation",
        event_message=f"QR / certificate ID verification completed with status {qr['qr_status']}.",
        status=VerificationEventStatus.COMPLETED if qr["qr_status"] == "verified" else VerificationEventStatus.WARNING,
    )
    certificate_id = qr.get("certificate_id") or fields.get("certificate_id")
    hash_result = verify_document_hash(db, source_path, certificate_id)
    add_verification_event(
        db,
        document_id=document.id,
        event_type="hash_verification",
        event_message=f"SHA-256 hash verification completed with status {hash_result['hash_status']}.",
        status=VerificationEventStatus.COMPLETED if hash_result["hash_status"] == "matched" else VerificationEventStatus.WARNING,
    )
    tamper = detect_document_tampering(source_path)
    add_verification_event(
        db,
        document_id=document.id,
        event_type="tamper_detection",
        event_message=f"Computer vision tamper detection completed with status {tamper['tampering_status']}.",
        status=VerificationEventStatus.WARNING if tamper["tampering_status"] in {"suspicious", "high_risk"} else VerificationEventStatus.COMPLETED,
    )

    detailed_results = {
        "ocr": {"structured_fields": fields, "text_length": len(extracted_text), "status": "warning" if ocr_warning else "completed", "message": ocr_warning},
        "metadata": metadata,
        "qr": qr,
        "hash": hash_result,
        "tamper": tamper,
    }
    score = calculate_authenticity_score(detailed_results)
    fraud_flags = collect_fraud_flags(metadata, qr, hash_result, tamper)
    explanation_cards = generate_issue_explanations(fraud_flags)
    add_verification_event(
        db,
        document_id=document.id,
        event_type="score_generation",
        event_message=f"Final authenticity score generated: {score['authenticity_score']}/100 ({score['risk_label']}).",
        status=VerificationEventStatus.COMPLETED,
    )
    add_verification_event(
        db,
        document_id=document.id,
        event_type="report_preparation",
        event_message="Verification report data was prepared for recruiter review.",
        status=VerificationEventStatus.COMPLETED,
    )

    verification.authenticity_score = score["authenticity_score"]
    verification.risk_level = score["risk_level"]
    verification.final_decision = score["final_decision"]
    verification.qr_status = qr["qr_status"]
    verification.hash_status = hash_result["hash_status"]
    verification.metadata_status = metadata["metadata_status"]
    verification.tampering_status = tamper["tampering_status"]
    verification.heatmap_path = tamper.get("heatmap_path")
    verification.issue_summary = "\n".join(score["issue_summary"])
    verification.detailed_results = serialize_results(detailed_results, score, explanation_cards)
    verification.recommendation = score["recommendation"]
    verification.ai_explanation = score["ai_explanation"]
    document.processing_status = DocumentProcessingStatus.COMPLETED

    replace_fraud_flags(db, verification, "metadata_", metadata["risk_flags"])
    replace_fraud_flags(db, verification, "qr_", qr["fraud_flags"])
    replace_fraud_flags(db, verification, "hash_", hash_result["fraud_flags"])
    replace_fraud_flags(db, verification, "tamper_", tamper["fraud_flags"])
    ensure_manual_review(db, verification)
    log_action(
        db,
        user=current_user,
        action="verification_completed",
        entity_type="uploaded_document",
        entity_id=document.id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=current_user.id,
        title="High-risk document" if score["authenticity_score"] < 55 else "Verification complete",
        message=f"{document.original_filename} scored {score['authenticity_score']}/100.",
        type=NotificationType.DANGER if score["authenticity_score"] < 55 else NotificationType.SUCCESS if score["authenticity_score"] >= 75 else NotificationType.WARNING,
    )
    db.commit()
    db.refresh(verification)

    return FullCheckResponse(
        verification_id=verification.id,
        document_id=document.id,
        authenticity_score=score["authenticity_score"],
        risk_level=score["risk_label"],
        final_decision=score["final_decision"].value,
        extracted_text=extracted_text,
        fraud_flags=fraud_flags,
        issue_summary=score["issue_summary"],
        detailed_results=serialize_results(detailed_results, score, explanation_cards),
        recommendation=score["recommendation"],
        explanation_cards=explanation_cards,
    )


@router.get("/documents/{document_id}/result", response_model=FullCheckResponse)
def get_saved_verification_result(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullCheckResponse:
    document = get_uploaded_document_or_404(db, document_id)
    ensure_verification_access(document, current_user)
    verification = document.verification_result
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification result not found. Start verification first.",
        )
    return build_full_check_response(document, verification)


@router.get("/{verification_id}/report")
def download_verification_report(
    verification_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    verification = db.get(VerificationResult, verification_id)
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification result not found.",
        )
    document = verification.document
    ensure_verification_access(document, current_user)
    report_path = Path(get_settings().report_dir) / f"verification_report_{verification.id}.pdf"
    generate_verification_report(
        report_path,
        {
            "document_id": document.id,
            "original_filename": document.original_filename,
            "uploaded_by": document.uploader.email if document.uploader else "Unknown user",
            "verification_date": verification.created_at.isoformat(),
            "authenticity_score": verification.authenticity_score,
            "risk_level": verification.risk_level.value,
            "final_decision": verification.final_decision.value,
            "extracted_text_summary": (verification.extracted_text or "")[:1200],
            "qr_status": verification.qr_status,
            "hash_status": verification.hash_status,
            "metadata_status": verification.metadata_status,
            "tampering_status": verification.tampering_status,
            "fraud_flags": [
                {
                    "severity": flag.severity.value,
                    "flag_type": flag.flag_type,
                    "message": flag.message,
                }
                for flag in verification.fraud_flags
            ],
            "ai_explanation": verification.ai_explanation,
            "recommendation": verification.recommendation,
            "explanation_cards": (verification.detailed_results or {}).get("score", {}).get("explanation_cards", []),
        },
    )
    log_action(
        db,
        user=current_user,
        action="report_downloaded",
        entity_type="verification_result",
        entity_id=verification.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return FileResponse(
        path=report_path,
        filename=f"docuverify-report-{verification.id}.pdf",
        media_type="application/pdf",
    )


@router.get("/{verification_id}/explanations", response_model=list[dict[str, Any]])
def get_verification_explanations(
    verification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    verification = db.get(VerificationResult, verification_id)
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification result not found.",
        )
    ensure_verification_access(verification.document, current_user)
    stored_cards = (verification.detailed_results or {}).get("score", {}).get("explanation_cards")
    if stored_cards:
        return stored_cards
    flags = [
        {
            "flag_type": flag.flag_type,
            "severity": flag.severity.value,
            "message": flag.message,
        }
        for flag in verification.fraud_flags
    ]
    return generate_issue_explanations(flags)


def build_full_check_response(document: UploadedDocument, verification: VerificationResult) -> FullCheckResponse:
    detailed_results = verification.detailed_results or {}
    explanation_cards = detailed_results.get("score", {}).get("explanation_cards", [])
    return FullCheckResponse(
        verification_id=verification.id,
        document_id=document.id,
        authenticity_score=verification.authenticity_score,
        risk_level=risk_label(verification.risk_level.value),
        final_decision=verification.final_decision.value,
        extracted_text=verification.extracted_text,
        fraud_flags=[
            {
                "flag_type": flag.flag_type,
                "severity": flag.severity.value,
                "message": flag.message,
                "region_coordinates": flag.region_coordinates,
            }
            for flag in verification.fraud_flags
        ],
        issue_summary=issue_summary_list(verification.issue_summary),
        detailed_results=detailed_results,
        recommendation=verification.recommendation or "",
        explanation_cards=explanation_cards,
    )


def issue_summary_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [line for line in value.splitlines() if line.strip()]


def risk_label(value: str) -> str:
    return {
        "very_low": "Very Low Risk",
        "low": "Low Risk",
        "medium": "Medium Risk",
        "high": "High Risk",
        "very_high": "Very High Risk",
        "critical": "Very High Risk",
    }.get(value, "Medium Risk")


def without_internal_flags(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "fraud_flags"}


def serialize_results(results: dict, score: dict, explanation_cards: list[dict] | None = None) -> dict:
    tamper = without_internal_flags(results["tamper"])
    if tamper.get("heatmap_path"):
        tamper["heatmap_url"] = asset_url(tamper["heatmap_path"], "processed")
    cleaned = {
        "ocr": results["ocr"],
        "metadata": without_internal_flags(results["metadata"]),
        "qr": without_internal_flags(results["qr"]),
        "hash": without_internal_flags(results["hash"]),
        "tamper": tamper,
        "score": {
            "component_scores": score["component_scores"],
            "risk_label": score["risk_label"],
            "explanation_cards": explanation_cards or [],
        },
    }
    return cleaned


def collect_fraud_flags(metadata: dict, qr: dict, hash_result: dict, tamper: dict) -> list[dict]:
    flags = []
    flags.extend(metadata.get("risk_flags", []))
    flags.extend(qr.get("fraud_flags", []))
    flags.extend(hash_result.get("fraud_flags", []))
    flags.extend(tamper.get("fraud_flags", []))
    return flags


def asset_url(file_path: str, mount_name: str) -> str:
    settings = get_settings()
    filename = file_path.replace("\\", "/").split("/")[-1]
    return f"{settings.public_base_url.rstrip('/')}/{mount_name}/{filename}"
