from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import VerificationEventStatus, enum_values


class VerificationEvent(Base):
    __tablename__ = "verification_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[VerificationEventStatus] = mapped_column(
        Enum(
            VerificationEventStatus,
            name="verification_event_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=VerificationEventStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    document: Mapped["UploadedDocument"] = relationship(back_populates="timeline_events")
