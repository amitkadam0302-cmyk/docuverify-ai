from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_recruiter_or_admin
from app.models import ManualReview, ManualReviewPriority, ManualReviewStatus, NotificationType, RiskLevel, UploadedDocument, User, VerificationResult
from app.schemas.workflows import (
    ManualReviewAssignRequest,
    ManualReviewCommentRequest,
    ManualReviewCreateRequest,
    ManualReviewDecisionRequest,
    ManualReviewResponse,
    ManualReviewStatusUpdateRequest,
)
from app.services.audit_service import log_action
from app.services.notification_service import create_notification

router = APIRouter(prefix="/reviews", tags=["manual reviews"])


@router.post("/create", response_model=ManualReviewResponse, status_code=status.HTTP_201_CREATED)
def create_manual_review(
    payload: ManualReviewCreateRequest,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    document = db.get(UploadedDocument, payload.document_id)
    if document is None or document.verification_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verified document not found.")
    verification = document.verification_result
    if verification.risk_level not in {RiskLevel.MEDIUM, RiskLevel.HIGH}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Medium or High risk documents can be sent to manual review from this workflow.",
        )
    existing = (
        db.query(ManualReview)
        .filter_by(document_id=document.id)
        .filter(ManualReview.status.in_([ManualReviewStatus.PENDING, ManualReviewStatus.IN_REVIEW]))
        .one_or_none()
    )
    if existing:
        return serialize_review(existing)
    review = ManualReview(
        document_id=document.id,
        verification_id=verification.id,
        assigned_to=payload.assigned_to,
        priority=payload.priority,
        status=ManualReviewStatus.PENDING,
    )
    db.add(review)
    db.flush()
    log_action(
        db,
        user=current_user,
        action="manual_review_created",
        entity_type="manual_review",
        entity_id=review.id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=payload.assigned_to or current_user.id,
        title="Manual review created",
        message=f"{document.original_filename} was sent to manual review.",
        type=NotificationType.WARNING,
    )
    db.commit()
    db.refresh(review)
    return serialize_review(review)


@router.get("/pending", response_model=list[ManualReviewResponse])
@router.get("", response_model=list[ManualReviewResponse])
def list_pending_reviews(
    status_filter: ManualReviewStatus | None = None,
    risk_level: RiskLevel | None = None,
    priority: ManualReviewPriority | None = None,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> list[ManualReviewResponse]:
    query = db.query(ManualReview).join(UploadedDocument).join(UploadedDocument.verification_result)
    if status_filter:
        query = query.filter(ManualReview.status == status_filter)
    else:
        query = query.filter(ManualReview.status.in_([ManualReviewStatus.PENDING, ManualReviewStatus.IN_REVIEW]))
    if risk_level:
        query = query.filter(VerificationResult.risk_level == risk_level)
    if priority:
        query = query.filter(ManualReview.priority == priority)
    return [serialize_review(review) for review in query.order_by(ManualReview.created_at.desc()).all()]


@router.get("/{review_id}", response_model=ManualReviewResponse)
def get_review(
    review_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    review = db.get(ManualReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual review not found.")
    return serialize_review(review)


@router.patch("/{review_id}/status", response_model=ManualReviewResponse)
def update_review_status(
    review_id: int,
    payload: ManualReviewStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    review = db.get(ManualReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual review not found.")
    review.status = payload.status
    review.reviewer_comment = payload.reviewer_comment
    review.final_decision = payload.status.value
    if review.assigned_to is None:
        review.assigned_to = current_user.id
    log_action(
        db,
        user=current_user,
        action="manual_review_status_updated",
        entity_type="manual_review",
        entity_id=review.id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=review.document.uploaded_by,
        title="Manual review updated",
        message=f"Review #{review.id} status changed to {payload.status.value}.",
        type=NotificationType.SUCCESS if payload.status == ManualReviewStatus.APPROVED else NotificationType.WARNING,
    )
    db.commit()
    db.refresh(review)
    return serialize_review(review)


@router.patch("/{review_id}/assign", response_model=ManualReviewResponse)
def assign_review(
    review_id: int,
    payload: ManualReviewAssignRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    review = db.get(ManualReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual review not found.")
    review.assigned_to = payload.assigned_to or current_user.id
    if payload.priority:
        review.priority = payload.priority
    if review.status == ManualReviewStatus.PENDING:
        review.status = ManualReviewStatus.IN_REVIEW
    create_notification(
        db,
        user_id=review.assigned_to,
        title="Review assigned",
        message=f"Manual review #{review.id} assigned.",
        type=NotificationType.INFO,
    )
    db.commit()
    db.refresh(review)
    return serialize_review(review)


@router.patch("/{review_id}/decision", response_model=ManualReviewResponse)
def decide_review(
    review_id: int,
    payload: ManualReviewDecisionRequest,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    review = db.get(ManualReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual review not found.")
    review.status = payload.status
    review.final_decision = payload.final_decision or payload.status.value
    review.reviewer_comment = payload.reviewer_comment
    review.assigned_to = review.assigned_to or current_user.id
    log_action(
        db,
        user=current_user,
        action="manual_review_decision",
        entity_type="manual_review",
        entity_id=review.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(review)
    return serialize_review(review)


@router.patch("/{review_id}/comment", response_model=ManualReviewResponse)
def comment_review(
    review_id: int,
    payload: ManualReviewCommentRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> ManualReviewResponse:
    review = db.get(ManualReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual review not found.")
    review.reviewer_comment = payload.reviewer_comment
    db.commit()
    db.refresh(review)
    return serialize_review(review)


def serialize_review(review: ManualReview) -> ManualReviewResponse:
    verification = review.verification
    return ManualReviewResponse(
        id=review.id,
        document_id=review.document_id,
        verification_id=review.verification_id,
        assigned_to=review.assigned_to,
        status=review.status,
        priority=review.priority,
        reviewer_comment=review.reviewer_comment,
        final_decision=review.final_decision,
        created_at=review.created_at,
        updated_at=review.updated_at,
        document={
            "id": review.document.id,
            "filename": review.document.original_filename,
            "document_type": review.document.document_type.value,
            "file_hash": review.document.file_hash,
        },
        verification={
            "authenticity_score": verification.authenticity_score if verification else 0,
            "risk_level": verification.risk_level.value if verification else "not_available",
            "final_decision": verification.final_decision.value if verification else "not_available",
            "extracted_text": verification.extracted_text if verification else "",
        },
        fraud_flags=[
            {"flag_type": flag.flag_type, "severity": flag.severity.value, "message": flag.message}
            for flag in (verification.fraud_flags if verification else [])
        ],
    )
