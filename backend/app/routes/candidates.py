from pathlib import Path
from uuid import uuid4

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_recruiter_or_admin
from app.models import CandidateDocument, CandidateProfile, NotificationType, TrustPassport, UploadedDocument, User
from app.schemas.workflows import (
    CandidateCreateRequest,
    CandidateLinkDocumentsRequest,
    CandidateProfileResponse,
    TrustPassportCreateRequest,
    TrustPassportResponse,
)
from app.services.audit_service import log_action
from app.services.candidate_service import build_candidate_summary
from app.services.notification_service import create_notification
from app.services.scoring_service import classify_risk

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateProfileResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreateRequest,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> CandidateProfileResponse:
    candidate = CandidateProfile(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        created_by=current_user.id,
    )
    db.add(candidate)
    db.flush()
    link_documents(db, candidate, payload.document_ids)
    log_action(
        db,
        user=current_user,
        action="candidate_profile_created",
        entity_type="candidate_profile",
        entity_id=candidate.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(candidate)
    return CandidateProfileResponse(**build_candidate_summary(candidate))


@router.get("", response_model=list[CandidateProfileResponse])
def list_candidates(
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> list[CandidateProfileResponse]:
    candidates = db.query(CandidateProfile).order_by(CandidateProfile.created_at.desc()).all()
    return [CandidateProfileResponse(**build_candidate_summary(candidate)) for candidate in candidates]


@router.get("/{candidate_id}", response_model=CandidateProfileResponse)
def get_candidate(
    candidate_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> CandidateProfileResponse:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return CandidateProfileResponse(**build_candidate_summary(candidate))


@router.patch("/{candidate_id}/documents", response_model=CandidateProfileResponse)
@router.post("/{candidate_id}/documents", response_model=CandidateProfileResponse)
def add_candidate_documents(
    candidate_id: int,
    payload: CandidateLinkDocumentsRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> CandidateProfileResponse:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    link_documents(db, candidate, payload.document_ids)
    db.commit()
    db.refresh(candidate)
    return CandidateProfileResponse(**build_candidate_summary(candidate))


@router.post("/trust-passport", response_model=TrustPassportResponse, status_code=status.HTTP_201_CREATED)
def create_trust_passport(
    payload: TrustPassportCreateRequest,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> TrustPassportResponse:
    candidate = db.get(CandidateProfile, payload.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    passport = generate_passport_for_candidate(db, candidate)
    log_action(
        db,
        user=current_user,
        action="trust_passport_created",
        entity_type="trust_passport",
        entity_id=passport.id,
        ip_address=request.client.host if request.client else None,
    )
    create_notification(
        db,
        user_id=current_user.id,
        title="Trust Passport created",
        message=f"Public trust passport generated for {candidate.full_name}.",
        type=NotificationType.SUCCESS,
    )
    db.commit()
    db.refresh(passport)
    return serialize_passport(passport)


@router.post("/{candidate_id}/generate-passport", response_model=TrustPassportResponse, status_code=status.HTTP_201_CREATED)
def generate_candidate_passport(
    candidate_id: int,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> TrustPassportResponse:
    candidate = db.get(CandidateProfile, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    passport = generate_passport_for_candidate(db, candidate)
    log_action(
        db,
        user=current_user,
        action="trust_passport_created",
        entity_type="trust_passport",
        entity_id=passport.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(passport)
    return serialize_passport(passport)


@router.get("/{candidate_id}/passport", response_model=TrustPassportResponse)
def get_candidate_passport(
    candidate_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> TrustPassportResponse:
    passport = (
        db.query(TrustPassport)
        .filter_by(candidate_id=candidate_id)
        .order_by(TrustPassport.created_at.desc())
        .first()
    )
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trust Passport not found.")
    return serialize_passport(passport)


@router.get("/trust-passport/{passport_id}", response_model=TrustPassportResponse)
def get_trust_passport(
    passport_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> TrustPassportResponse:
    passport = db.get(TrustPassport, passport_id)
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trust Passport not found.")
    return serialize_passport(passport)


def link_documents(db: Session, candidate: CandidateProfile, document_ids: list[int]) -> None:
    existing_ids = {link.document_id for link in candidate.documents}
    for document_id in document_ids:
        if document_id in existing_ids:
            continue
        document = db.get(UploadedDocument, document_id)
        if document is not None:
            db.add(
                CandidateDocument(
                    candidate_id=candidate.id,
                    document_id=document_id,
                    document_category=document.document_type.value,
                )
            )


def generate_passport_for_candidate(db: Session, candidate: CandidateProfile) -> TrustPassport:
    token = uuid4().hex[:16]
    public_url = f"{get_settings().frontend_url.rstrip('/')}/passport/{token}"
    qr_image_path = generate_passport_qr(public_url, token)
    scores = calculate_passport_scores(candidate)
    passport = TrustPassport(
        candidate_id=candidate.id,
        public_slug=token,
        public_token=token,
        qr_image_path=qr_image_path,
        **scores,
    )
    db.add(passport)
    db.flush()
    return passport


def calculate_passport_scores(candidate: CandidateProfile) -> dict:
    buckets = {"education": [], "certificate": [], "experience": [], "resume": []}
    all_scores = []
    for link in candidate.documents:
        verification = link.document.verification_result
        if not verification:
            continue
        score = float(verification.authenticity_score or 0)
        all_scores.append(score)
        document_type = link.document.document_type.value
        if document_type in {"certificate", "marksheet"}:
            buckets["education"].append(score)
            buckets["certificate"].append(score)
        elif document_type == "experience_letter":
            buckets["experience"].append(score)
        elif document_type == "resume":
            buckets["resume"].append(score)
    overall = average(all_scores)
    _, risk_level = classify_risk(overall)
    return {
        "overall_score": overall,
        "education_score": average(buckets["education"]),
        "certificate_score": average(buckets["certificate"]),
        "experience_score": average(buckets["experience"]),
        "resume_score": average(buckets["resume"]),
        "risk_level": risk_level.value,
    }


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def generate_passport_qr(public_url: str, slug: str) -> str:
    settings = get_settings()
    output_dir = Path(settings.generated_qr_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"trust_passport_{slug}.png"
    image = qrcode.make(public_url)
    image.save(path)
    return str(path)


def serialize_passport(passport: TrustPassport) -> TrustPassportResponse:
    settings = get_settings()
    filename = passport.qr_image_path.replace("\\", "/").split("/")[-1] if passport.qr_image_path else None
    token = passport.public_token or passport.public_slug
    public_url = f"{settings.frontend_url.rstrip('/')}/passport/{token}"
    return TrustPassportResponse(
        id=passport.id,
        candidate_id=passport.candidate_id,
        public_slug=passport.public_slug,
        public_token=token,
        public_url=public_url,
        qr_image_url=f"{settings.public_base_url.rstrip('/')}/generated_qr/{filename}" if filename else None,
        overall_score=passport.overall_score,
        education_score=passport.education_score,
        certificate_score=passport.certificate_score,
        experience_score=passport.experience_score,
        resume_score=passport.resume_score,
        risk_level=passport.risk_level,
        candidate=CandidateProfileResponse(**build_candidate_summary(passport.candidate)),
    )
