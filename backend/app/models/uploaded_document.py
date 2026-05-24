from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DocumentProcessingStatus, DocumentType, enum_values


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="document_type",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(
            DocumentProcessingStatus,
            name="document_processing_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=DocumentProcessingStatus.PENDING,
        nullable=False,
    )

    uploader: Mapped["User | None"] = relationship(back_populates="uploaded_documents")
    workspace: Mapped["Workspace | None"] = relationship(back_populates="documents")
    verification_result: Mapped["VerificationResult | None"] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    manual_reviews: Mapped[list["ManualReview"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    timeline_events: Mapped[list["VerificationEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    batch_links: Mapped[list["BatchDocument"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    candidate_links: Mapped[list["CandidateDocument"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
