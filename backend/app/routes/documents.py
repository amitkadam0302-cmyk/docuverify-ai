from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, is_admin
from app.models import DocumentType, NotificationType, UploadedDocument, User, VerificationEvent, VerificationEventStatus, WorkspaceMember, WorkspaceMemberStatus
from app.schemas.documents import DocumentResponse, DocumentSignedUrlResponse, DocumentUploadResponse
from app.schemas.workflows import VerificationEventResponse
from app.services.audit_service import log_action
from app.services.notification_service import create_notification
from app.services.timeline_service import add_verification_event
from app.services.storage_service import create_signed_url, delete_file, upload_file, validate_local_preview_signature

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_or_404(db: Session, document_id: int) -> UploadedDocument:
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document


def ensure_owner_or_admin(document: UploadedDocument, current_user: User) -> None:
    if document.uploaded_by == current_user.id or is_admin(current_user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the document owner or an administrator can access this document.",
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    settings = get_settings()
    stored_file = await upload_file(file)

    uploaded_document = UploadedDocument(
        uploaded_by=current_user.id,
        workspace_id=current_workspace_id(db, current_user),
        document_type=document_type,
        original_filename=stored_file.original_filename,
        file_path=stored_file.storage_path,
        file_hash=stored_file.file_hash,
    )
    db.add(uploaded_document)
    db.flush()
    add_verification_event(
        db,
        document_id=uploaded_document.id,
        event_type="upload_received",
        event_message="Document was uploaded and SHA-256 hash was calculated.",
        status=VerificationEventStatus.COMPLETED,
    )
    log_action(
        db,
        user=current_user,
        action="document_uploaded",
        entity_type="uploaded_document",
        entity_id=uploaded_document.id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=current_user.id,
        title="Document uploaded",
        message=f"{uploaded_document.original_filename} is ready for verification.",
        type=NotificationType.INFO,
    )
    db.commit()
    db.refresh(uploaded_document)

    return DocumentUploadResponse(
        document_id=uploaded_document.id,
        original_filename=uploaded_document.original_filename,
        file_hash=uploaded_document.file_hash,
        document_type=uploaded_document.document_type,
        processing_status=uploaded_document.processing_status,
    )


@router.get("/my-documents", response_model=list[DocumentResponse])
def list_my_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UploadedDocument]:
    return (
        db.query(UploadedDocument)
        .filter_by(uploaded_by=current_user.id)
        .order_by(UploadedDocument.upload_time.desc())
        .all()
    )


@router.get("/local-preview/{filename}")
def get_local_preview(
    filename: str,
    expires: int = Query(...),
    signature: str = Query(...),
) -> FileResponse:
    if not validate_local_preview_signature(filename, expires, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Preview link has expired.")
    path = Path(get_settings().upload_dir) / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")
    return FileResponse(path)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadedDocument:
    document = get_document_or_404(db, document_id)
    ensure_owner_or_admin(document, current_user)
    return document


@router.get("/{document_id}/signed-url", response_model=DocumentSignedUrlResponse)
def get_document_signed_url(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentSignedUrlResponse:
    document = get_document_or_404(db, document_id)
    ensure_owner_or_admin(document, current_user)
    expires_in = 900
    return DocumentSignedUrlResponse(
        document_id=document.id,
        signed_url=create_signed_url(document.file_path, expires_in=expires_in),
        expires_in=expires_in,
    )


@router.get("/{document_id}/timeline", response_model=list[VerificationEventResponse])
def get_document_timeline(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VerificationEvent]:
    document = get_document_or_404(db, document_id)
    ensure_owner_or_admin(document, current_user)
    return (
        db.query(VerificationEvent)
        .filter_by(document_id=document.id)
        .order_by(VerificationEvent.created_at.asc())
        .all()
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document = get_document_or_404(db, document_id)
    ensure_owner_or_admin(document, current_user)
    delete_file(document.file_path)
    db.delete(document)
    db.commit()


def current_workspace_id(db: Session, user: User) -> int | None:
    membership = (
        db.query(WorkspaceMember)
        .filter_by(user_id=user.id, status=WorkspaceMemberStatus.ACTIVE)
        .order_by(WorkspaceMember.created_at.asc())
        .first()
    )
    return membership.workspace_id if membership else None
