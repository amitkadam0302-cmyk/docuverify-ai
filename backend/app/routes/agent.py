from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, is_admin
from app.models import NotificationType, UploadedDocument, User, UserRole
from app.schemas.workflows import AgentVerifyResponse
from app.services.audit_service import log_action
from app.services.notification_service import create_notification
from app.services.ocr_service import OCRUnavailableError
from app.services.verification_agent import run_verification_agent

router = APIRouter(prefix="/agent", tags=["ai verification agent"])


@router.post("/verify/{document_id}", response_model=AgentVerifyResponse)
def verify_with_agent(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentVerifyResponse:
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.uploaded_by != current_user.id and current_user.role != UserRole.RECRUITER and not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to verify this document.")
    log_action(
        db,
        user=current_user,
        action="verification_started",
        entity_type="uploaded_document",
        entity_id=document.id,
        ip_address=request.client.host if request.client else None,
    )
    try:
        result = run_verification_agent(db, document)
    except OCRUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored document file was not found.") from exc

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
        title="Agent verification complete",
        message=f"{document.original_filename} scored {result['final_score']}/100.",
        type=NotificationType.SUCCESS if result["final_score"] >= 75 else NotificationType.WARNING,
    )
    db.commit()
    return AgentVerifyResponse(**result)
