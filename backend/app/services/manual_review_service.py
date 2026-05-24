from sqlalchemy.orm import Session

from app.models import (
    ManualReview,
    ManualReviewPriority,
    ManualReviewStatus,
    VerificationResult,
)


def priority_from_score(score: float) -> ManualReviewPriority:
    if score < 35:
        return ManualReviewPriority.CRITICAL
    if score < 55:
        return ManualReviewPriority.HIGH
    if score < 75:
        return ManualReviewPriority.MEDIUM
    return ManualReviewPriority.LOW


def should_create_manual_review(verification: VerificationResult) -> bool:
    detailed = verification.detailed_results or {}
    score = verification.authenticity_score or 0
    qr = detailed.get("qr", {})
    hash_result = detailed.get("hash", {})
    metadata = detailed.get("metadata", {})
    tamper = detailed.get("tamper", {})
    explanation = (verification.ai_explanation or "").lower()

    return any(
        [
            35 <= score <= 74,
            qr.get("qr_status") not in {"verified", None, "skipped"} and hash_result.get("hash_status") == "matched",
            metadata.get("metadata_status") in {"suspicious", "high_risk"},
            float(tamper.get("tamper_score") or 0) >= 35,
            "manual review" in explanation,
        ]
    )


def ensure_manual_review(
    db: Session,
    verification: VerificationResult,
    assigned_to: int | None = None,
    priority: ManualReviewPriority | None = None,
) -> ManualReview | None:
    """Create one active review per document when automated checks need human judgment."""
    if not should_create_manual_review(verification):
        return None

    existing = (
        db.query(ManualReview)
        .filter_by(document_id=verification.document_id)
        .filter(ManualReview.status.in_([ManualReviewStatus.PENDING, ManualReviewStatus.IN_REVIEW]))
        .one_or_none()
    )
    if existing:
        return existing

    review = ManualReview(
        document_id=verification.document_id,
        verification_id=verification.id,
        assigned_to=assigned_to,
        priority=priority or priority_from_score(verification.authenticity_score),
        status=ManualReviewStatus.PENDING,
    )
    db.add(review)
    db.flush()
    return review
