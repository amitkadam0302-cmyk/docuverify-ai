from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BatchVerificationStatus, enum_values


class BatchVerification(Base):
    __tablename__ = "batch_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_documents: Mapped[int] = mapped_column(default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(default=0, nullable=False)
    completed_documents: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_documents: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[BatchVerificationStatus] = mapped_column(
        Enum(
            BatchVerificationStatus,
            name="batch_verification_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=BatchVerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    uploader: Mapped["User | None"] = relationship(back_populates="batch_verifications")
    documents: Mapped[list["BatchDocument"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class BatchDocument(Base):
    __tablename__ = "batch_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batch_verifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[BatchVerificationStatus] = mapped_column(
        Enum(
            BatchVerificationStatus,
            name="batch_document_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=BatchVerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    batch: Mapped["BatchVerification"] = relationship(back_populates="documents")
    document: Mapped["UploadedDocument"] = relationship(back_populates="batch_links")
