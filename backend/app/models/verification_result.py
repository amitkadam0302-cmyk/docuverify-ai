from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FinalDecision, RiskLevel, enum_values


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    authenticity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=RiskLevel.MEDIUM,
        nullable=False,
    )
    final_decision: Mapped[FinalDecision] = mapped_column(
        Enum(
            FinalDecision,
            name="final_decision",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=FinalDecision.REVIEW_REQUIRED,
        nullable=False,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    hash_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    tampering_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    institution_match_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailed_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    heatmap_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    document: Mapped["UploadedDocument"] = relationship(
        back_populates="verification_result"
    )
    fraud_flags: Mapped[list["FraudFlag"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan"
    )
    manual_reviews: Mapped[list["ManualReview"]] = relationship(
        back_populates="verification"
    )
