from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_recruiter_or_admin
from app.models import (
    BatchDocument,
    BatchVerification,
    BatchVerificationStatus,
    DocumentProcessingStatus,
    DocumentType,
    NotificationType,
    UploadedDocument,
    User,
    VerificationEventStatus,
    WorkspaceMember,
    WorkspaceMemberStatus,
)
from app.schemas.workflows import BatchCreateRequest, BatchResultResponse, BatchUploadResponse
from app.services.audit_service import log_action
from app.services.explanation_service import generate_issue_explanations
from app.services.hash_service import verify_document_hash
from app.services.metadata_service import analyze_document_metadata
from app.services.notification_service import create_notification
from app.services.ocr_service import OCRUnavailableError, extract_document_text, extract_structured_fields
from app.services.qr_service import verify_qr_certificate
from app.services.report_service import generate_basic_report
from app.services.scoring_service import calculate_authenticity_score
from app.services.storage_service import upload_file
from app.services.tamper_service import detect_document_tampering
from app.services.timeline_service import add_verification_event
from app.services.verification_result_service import get_or_create_verification_result, replace_fraud_flags

router = APIRouter(prefix="/batch", tags=["batch verification"])


@router.post("/create", response_model=BatchResultResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreateRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> BatchResultResponse:
    batch = BatchVerification(
        uploaded_by=current_user.id,
        batch_name=payload.batch_name,
        total_documents=0,
        completed_count=0,
        completed_documents=0,
        failed_documents=0,
        status=BatchVerificationStatus.PENDING,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return serialize_batch(batch)


@router.post("/upload", response_model=BatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_batch(
    request: Request,
    batch_name: str = Form(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> BatchUploadResponse:
    batch = BatchVerification(
        uploaded_by=current_user.id,
        batch_name=batch_name,
        total_documents=len(files),
        completed_count=0,
        completed_documents=0,
        failed_documents=0,
        status=BatchVerificationStatus.PENDING,
    )
    db.add(batch)
    db.flush()
    documents = await add_files_to_batch(db, batch, files, document_type, current_user.id)
    log_action(
        db,
        user=current_user,
        action="batch_upload",
        entity_type="batch_verification",
        entity_id=batch.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return BatchUploadResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        total_documents=batch.total_documents,
        completed_count=batch.completed_count,
        status=batch.status,
        documents=documents,
    )


@router.post("/{batch_id}/upload", response_model=BatchUploadResponse)
async def upload_to_existing_batch(
    batch_id: int,
    document_type: DocumentType = Form(DocumentType.OTHER),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> BatchUploadResponse:
    batch = db.get(BatchVerification, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    documents = await add_files_to_batch(db, batch, files, document_type, current_user.id)
    batch.total_documents += len(files)
    db.commit()
    db.refresh(batch)
    return BatchUploadResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        total_documents=batch.total_documents,
        completed_count=batch.completed_count,
        status=batch.status,
        documents=documents,
    )


@router.post("/{batch_id}/verify", response_model=BatchResultResponse)
def verify_batch(
    batch_id: int,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> BatchResultResponse:
    batch = db.get(BatchVerification, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    batch.status = BatchVerificationStatus.PROCESSING
    db.flush()
    completed = 0
    failed = 0
    for link in batch.documents:
        try:
            verification = run_document_check(db, link.document)
            link.status = BatchVerificationStatus.COMPLETED
            link.score = verification.authenticity_score
            link.risk_level = verification.risk_level.value
            link.error_message = None
            completed += 1
        except Exception as exc:
            link.status = BatchVerificationStatus.FAILED
            link.error_message = str(exc)[:500]
            link.document.processing_status = DocumentProcessingStatus.FAILED
            add_verification_event(
                db,
                document_id=link.document_id,
                event_type="batch_verification_failed",
                event_message="Batch verification failed for this document.",
                status=VerificationEventStatus.FAILED,
            )
            failed += 1
    batch.completed_count = completed
    batch.completed_documents = completed
    batch.failed_documents = failed
    batch.status = BatchVerificationStatus.COMPLETED if completed == batch.total_documents else BatchVerificationStatus.FAILED
    log_action(
        db,
        user=current_user,
        action="batch_verification",
        entity_type="batch_verification",
        entity_id=batch.id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=current_user.id,
        title="Batch verification complete",
        message=f"{completed}/{batch.total_documents} documents completed in {batch.batch_name}.",
        type=NotificationType.SUCCESS if completed == batch.total_documents else NotificationType.WARNING,
    )
    db.commit()
    db.refresh(batch)
    return serialize_batch(batch)


@router.get("", response_model=list[BatchResultResponse])
def list_batches(
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> list[BatchResultResponse]:
    batches = db.query(BatchVerification).order_by(BatchVerification.created_at.desc()).all()
    return [serialize_batch(batch) for batch in batches]


@router.get("/{batch_id}", response_model=BatchResultResponse)
def get_batch(
    batch_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> BatchResultResponse:
    batch = db.get(BatchVerification, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    return serialize_batch(batch)


@router.get("/{batch_id}/results", response_model=BatchResultResponse)
def get_batch_results(
    batch_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> BatchResultResponse:
    batch = db.get(BatchVerification, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    return serialize_batch(batch)


@router.get("/{batch_id}/summary.csv")
@router.get("/{batch_id}/export-csv")
def download_batch_csv(
    batch_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    batch = db.get(BatchVerification, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    lines = ["filename,document_type,authenticity_score,risk_level,final_decision"]
    for item in serialize_batch(batch).results:
        lines.append(
            f"\"{item['filename']}\",{item['document_type']},{item['authenticity_score']},{item['risk_level']},{item['final_decision']}"
        )
    return PlainTextResponse("\n".join(lines), media_type="text/csv")


@router.get("/{batch_id}/summary.pdf")
def download_batch_pdf(
    batch_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> FileResponse:
    batch = db.get(BatchVerification, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    path = Path(get_settings().report_dir) / f"batch_summary_{batch.id}.pdf"
    generate_basic_report(
        path,
        "DocuVerify AI Batch Verification Summary",
        f"{batch.batch_name}: {batch.completed_count}/{batch.total_documents} documents completed.",
    )
    return FileResponse(path, filename=f"batch-summary-{batch.id}.pdf", media_type="application/pdf")


async def add_files_to_batch(
    db: Session,
    batch: BatchVerification,
    files: list[UploadFile],
    document_type: DocumentType,
    user_id: int,
) -> list[dict]:
    settings = get_settings()
    documents = []
    for file in files:
        stored_file = await upload_file(file)
        document = UploadedDocument(
            uploaded_by=user_id,
            workspace_id=current_workspace_id(db, user_id),
            document_type=document_type,
            original_filename=stored_file.original_filename,
            file_path=stored_file.storage_path,
            file_hash=stored_file.file_hash,
        )
        db.add(document)
        db.flush()
        db.add(BatchDocument(batch_id=batch.id, document_id=document.id, status=BatchVerificationStatus.PENDING))
        add_verification_event(
            db,
            document_id=document.id,
            event_type="batch_upload",
            event_message=f"Document uploaded as part of batch '{batch.batch_name}'.",
            status=VerificationEventStatus.COMPLETED,
        )
        documents.append(
            {
                "document_id": document.id,
                "filename": document.original_filename,
                "document_type": document.document_type.value,
                "file_hash": document.file_hash,
            }
        )
    return documents


def current_workspace_id(db: Session, user_id: int) -> int | None:
    membership = (
        db.query(WorkspaceMember)
        .filter_by(user_id=user_id, status=WorkspaceMemberStatus.ACTIVE)
        .order_by(WorkspaceMember.created_at.asc())
        .first()
    )
    return membership.workspace_id if membership else None


def run_document_check(db: Session, document: UploadedDocument):
    verification = get_or_create_verification_result(db, document_id=document.id)
    extracted_text = extract_document_text(document.file_path)
    fields = extract_structured_fields(extracted_text)
    verification.extracted_text = extracted_text
    metadata = analyze_document_metadata(document.file_path, fields.get("issue_date"))
    qr = verify_qr_certificate(db, document.file_path, fields)
    certificate_id = qr.get("certificate_id") or fields.get("certificate_id")
    hash_result = verify_document_hash(db, document.file_path, certificate_id)
    tamper = detect_document_tampering(document.file_path)
    detailed_results = {
        "ocr": {"structured_fields": fields, "text_length": len(extracted_text)},
        "metadata": metadata,
        "qr": qr,
        "hash": hash_result,
        "tamper": tamper,
    }
    score = calculate_authenticity_score(detailed_results)
    flags = []
    flags.extend(metadata.get("risk_flags", []))
    flags.extend(qr.get("fraud_flags", []))
    flags.extend(hash_result.get("fraud_flags", []))
    flags.extend(tamper.get("fraud_flags", []))
    verification.authenticity_score = score["authenticity_score"]
    verification.risk_level = score["risk_level"]
    verification.final_decision = score["final_decision"]
    verification.qr_status = qr["qr_status"]
    verification.hash_status = hash_result["hash_status"]
    verification.metadata_status = metadata["metadata_status"]
    verification.tampering_status = tamper["tampering_status"]
    verification.issue_summary = "\n".join(score["issue_summary"])
    verification.recommendation = score["recommendation"]
    verification.ai_explanation = score["ai_explanation"]
    verification.detailed_results = {
        "ocr": detailed_results["ocr"],
        "metadata": {key: value for key, value in metadata.items() if key != "risk_flags"},
        "qr": {key: value for key, value in qr.items() if key != "fraud_flags"},
        "hash": {key: value for key, value in hash_result.items() if key != "fraud_flags"},
        "tamper": {key: value for key, value in tamper.items() if key != "fraud_flags"},
        "score": {
            "component_scores": score["component_scores"],
            "risk_label": score["risk_label"],
            "explanation_cards": generate_issue_explanations(flags),
        },
    }
    document.processing_status = DocumentProcessingStatus.COMPLETED
    replace_fraud_flags(db, verification, "metadata_", metadata["risk_flags"])
    replace_fraud_flags(db, verification, "qr_", qr["fraud_flags"])
    replace_fraud_flags(db, verification, "hash_", hash_result["fraud_flags"])
    replace_fraud_flags(db, verification, "tamper_", tamper["fraud_flags"])
    add_verification_event(
        db,
        document_id=document.id,
        event_type="batch_verification_complete",
        event_message=f"Batch verification completed with score {score['authenticity_score']}/100.",
        status=VerificationEventStatus.COMPLETED,
    )
    return verification


def serialize_batch(batch: BatchVerification) -> BatchResultResponse:
    results = []
    for link in batch.documents:
        document = link.document
        verification = document.verification_result
        results.append(
            {
                "document_id": document.id,
                "filename": document.original_filename,
                "document_type": document.document_type.value,
                "authenticity_score": verification.authenticity_score if verification else 0,
                "risk_level": verification.risk_level.value if verification else "not_verified",
                "final_decision": verification.final_decision.value if verification else "not_verified",
                "status": link.status.value,
                "error_message": link.error_message,
            }
        )
    return BatchResultResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        total_documents=batch.total_documents,
        completed_count=batch.completed_count,
        completed_documents=batch.completed_documents or batch.completed_count,
        failed_documents=batch.failed_documents,
        status=batch.status,
        results=results,
    )
