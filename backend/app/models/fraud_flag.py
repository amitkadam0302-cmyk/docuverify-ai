from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FraudSeverity, enum_values


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    verification_id: Mapped[int] = mapped_column(
        ForeignKey("verification_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[FraudSeverity] = mapped_column(
        Enum(
            FraudSeverity,
            name="fraud_severity",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=FraudSeverity.INFO,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    region_coordinates: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    verification: Mapped["VerificationResult"] = relationship(back_populates="fraud_flags")
