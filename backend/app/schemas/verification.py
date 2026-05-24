from typing import Any

from pydantic import BaseModel


class OCRResponse(BaseModel):
    document_id: int
    extracted_text: str
    structured_fields: dict[str, Any]


class MetadataResponse(BaseModel):
    document_id: int
    metadata_summary: dict[str, Any]
    risk_flags: list[dict[str, Any]]
    metadata_status: str
    risk_score_component: float


class QRVerifyResponse(BaseModel):
    qr_found: bool
    qr_value: str | None
    certificate_id: str | None
    database_match: bool
    match_details: dict[str, Any]
    qr_status: str


class HashVerifyResponse(BaseModel):
    uploaded_hash: str
    registered_hash: str | None
    hash_match: bool
    hash_status: str
    explanation: str


class TamperDetectResponse(BaseModel):
    tampering_status: str
    suspicious_regions: list[dict[str, Any]]
    tamper_score: float
    heatmap_path: str
    explanation: str


class ResumeConsistencyRequest(BaseModel):
    resume_document_id: int
    supporting_document_ids: list[int]


class ResumeConsistencyResponse(BaseModel):
    consistency_score: float
    mismatches: list[dict[str, Any]]
    explanation: str
    recommendation: str


class FullCheckResponse(BaseModel):
    verification_id: int
    document_id: int
    authenticity_score: float
    risk_level: str
    final_decision: str
    extracted_text: str | None
    fraud_flags: list[dict[str, Any]]
    issue_summary: list[str]
    detailed_results: dict[str, Any]
    recommendation: str
    explanation_cards: list[dict[str, Any]] = []
