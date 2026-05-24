from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VerificationLedger(Base):
    __tablename__ = "verification_ledgers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    certificate_id: Mapped[str] = mapped_column(
        ForeignKey("certificates.certificate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)

    certificate: Mapped["Certificate"] = relationship(back_populates="ledger_entries")
