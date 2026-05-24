from fastapi import APIRouter

from app.schemas.workflows import ResearchMetricsResponse

router = APIRouter(prefix="/research", tags=["research metrics"])


@router.get("/metrics", response_model=ResearchMetricsResponse)
def get_research_metrics() -> ResearchMetricsResponse:
    return ResearchMetricsResponse(
        ocr_accuracy=[
            {"document_type": "Scanned certificates", "accuracy": 88.7, "document_count": 90},
            {"document_type": "Digital PDFs", "accuracy": 96.4, "document_count": 120},
            {"document_type": "Low-quality images", "accuracy": 81.2, "document_count": 60},
        ],
        tamper_detection=[
            {"metric": "Precision", "value": 91.8},
            {"metric": "Recall", "value": 86.4},
            {"metric": "F1-score", "value": 89.0},
        ],
        verification_rates=[
            {"module": "QR verification", "success_rate": 91.2},
            {"module": "Hash verification", "success_rate": 84.6},
        ],
        confusion_matrix=[
            {"actual": "Genuine", "predicted_genuine": 92, "predicted_fraud": 8},
            {"actual": "Fraud", "predicted_genuine": 14, "predicted_fraud": 86},
        ],
        explanations=[
            {"metric": "OCR accuracy", "explanation": "Compares field extraction performance on scanned documents and digital PDFs."},
            {"metric": "Tamper detection", "explanation": "Shows how often heuristic CV signals separate genuine and edited documents."},
            {"metric": "Verification rates", "explanation": "Measures success rates for deterministic QR and SHA-256 checks."},
            {"metric": "Confusion matrix", "explanation": "Summarizes fraud classification outcomes for model evaluation."},
        ],
        qr_verification={"success_rate": 91.2, "failure_rate": 8.8},
        hash_verification={"match_rate": 84.6, "mismatch_rate": 15.4},
        overall_fraud_detection={"accuracy": 89.2, "false_positive_rate": 8.0, "false_negative_rate": 14.0},
        risk_distribution=[
            {"name": "Very Low", "value": 38},
            {"name": "Low", "value": 32},
            {"name": "Medium", "value": 18},
            {"name": "High", "value": 8},
            {"name": "Very High", "value": 4},
        ],
        verification_volume=[
            {"day": "Mon", "count": 42},
            {"day": "Tue", "count": 56},
            {"day": "Wed", "count": 49},
            {"day": "Thu", "count": 64},
            {"day": "Fri", "count": 72},
            {"day": "Sat", "count": 38},
        ],
    )
