from sqlalchemy.orm import Session

from app.models import FraudFlag, FraudSeverity, VerificationResult


def get_or_create_verification_result(
    db: Session,
    document_id: int,
) -> VerificationResult:
    verification = (
        db.query(VerificationResult).filter_by(document_id=document_id).one_or_none()
    )
    if verification is None:
        verification = VerificationResult(document_id=document_id)
        db.add(verification)
        db.flush()
    return verification


def replace_fraud_flags(
    db: Session,
    verification: VerificationResult,
    prefix: str,
    flags: list[dict],
) -> None:
    for existing_flag in list(verification.fraud_flags):
        if existing_flag.flag_type.startswith(prefix):
            db.delete(existing_flag)

    db.flush()
    for flag in flags:
        db.add(
            FraudFlag(
                verification_id=verification.id,
                flag_type=flag["flag_type"],
                severity=FraudSeverity(flag.get("severity", "medium")),
                message=flag["message"],
                region_coordinates=flag.get("region_coordinates"),
            )
        )
