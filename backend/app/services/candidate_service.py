from typing import Any

from app.models import CandidateProfile, FinalDecision


def build_candidate_summary(candidate: CandidateProfile) -> dict[str, Any]:
    document_rows = []
    scores = []
    mismatches = []
    verified_education = []
    verified_certificates = []
    verified_experience = []

    for link in candidate.documents:
        document = link.document
        verification = document.verification_result
        score = verification.authenticity_score if verification else 0.0
        risk_level = verification.risk_level.value if verification else "not_verified"
        decision = verification.final_decision.value if verification else "not_verified"
        document_rows.append(
            {
                "document_id": document.id,
                "filename": document.original_filename,
                "document_type": document.document_type.value,
                "authenticity_score": score,
                "risk_level": risk_level,
                "final_decision": decision,
            }
        )
        if verification:
            scores.append(score)
            if verification.issue_summary:
                mismatches.extend(
                    [line for line in verification.issue_summary.splitlines() if line.strip()]
                )
            if verification.final_decision == FinalDecision.VERIFIED:
                if document.document_type.value in {"certificate", "marksheet"}:
                    verified_education.append(document.original_filename)
                    verified_certificates.append(document.original_filename)
                if document.document_type.value == "experience_letter":
                    verified_experience.append(document.original_filename)

    overall_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    recommendation = (
        "Candidate profile is suitable for standard recruiter processing."
        if overall_score >= 80
        else "Candidate profile should be manually reviewed before approval."
        if overall_score >= 55
        else "Candidate profile is high risk until documents are independently verified."
    )
    return {
        "candidate_id": candidate.id,
        "full_name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "uploaded_documents": document_rows,
        "overall_trust_score": overall_score,
        "mismatch_summary": mismatches[:12],
        "final_recommendation": recommendation,
        "verified_education": verified_education,
        "verified_certificates": verified_certificates,
        "verified_experience": verified_experience,
    }
