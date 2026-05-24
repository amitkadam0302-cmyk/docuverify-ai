from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_recruiter_or_admin
from app.models import FinalDecision, UploadedDocument, User, VerificationResult

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/recruiter-stats")
def get_recruiter_stats(
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    verifications = db.query(VerificationResult).join(UploadedDocument).all()
    total = len(verifications)
    decisions = Counter(result.final_decision for result in verifications)
    risks = Counter(result.risk_level.value for result in verifications)
    scored = [result.authenticity_score for result in verifications]

    recent = []
    for result in sorted(verifications, key=lambda item: item.created_at, reverse=True)[:10]:
        details = result.detailed_results or {}
        fields = details.get("ocr", {}).get("structured_fields", {})
        recent.append(
            {
                "verification_id": result.id,
                "document_id": result.document_id,
                "filename": result.document.original_filename,
                "candidate_name": fields.get("candidate_name"),
                "certificate_id": fields.get("certificate_id")
                or details.get("qr", {}).get("certificate_id"),
                "risk_level": result.risk_level.value,
                "final_decision": result.final_decision.value,
                "authenticity_score": result.authenticity_score,
                "created_at": result.created_at.isoformat(),
            }
        )

    return {
        "total_documents_verified": total,
        "verified_count": decisions[FinalDecision.VERIFIED],
        "manual_review_count": decisions[FinalDecision.MANUAL_REVIEW_REQUIRED]
        + decisions[FinalDecision.REVIEW_REQUIRED],
        "likely_fraud_count": decisions[FinalDecision.LIKELY_FRAUD]
        + decisions[FinalDecision.FRAUDULENT],
        "rejected_count": decisions[FinalDecision.REJECTED],
        "average_authenticity_score": round(sum(scored) / total, 2) if total else 0.0,
        "recent_verifications": recent,
        "risk_distribution": [
            {"risk_level": risk_level, "count": count}
            for risk_level, count in sorted(risks.items())
        ],
    }
