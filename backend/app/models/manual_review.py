from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ManualReviewPriority, ManualReviewStatus, enum_values


class ManualReview(Base):
    __tablename__ = "manual_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_id: Mapped[int | None] = mapped_column(
        ForeignKey("verification_results.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[ManualReviewStatus] = mapped_column(
        Enum(
            ManualReviewStatus,
            name="manual_review_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=ManualReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[ManualReviewPriority] = mapped_column(
        Enum(
            ManualReviewPriority,
            name="manual_review_priority",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=ManualReviewPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    reviewer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    document: Mapped["UploadedDocument"] = relationship(back_populates="manual_reviews")
    verification: Mapped["VerificationResult | None"] = relationship(back_populates="manual_reviews")
    reviewer: Mapped["User | None"] = relationship(back_populates="assigned_reviews")
