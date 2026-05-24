from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CertificateStatus, enum_values


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    certificate_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    qr_code_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[CertificateStatus] = mapped_column(
        Enum(
            CertificateStatus,
            name="certificate_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=CertificateStatus.VALID,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    institution: Mapped["Institution"] = relationship(back_populates="certificates")
    ledger_entries: Mapped[list["VerificationLedger"]] = relationship(
        back_populates="certificate", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_certificates_certificate_hash", "certificate_id", "document_hash"),
    )
