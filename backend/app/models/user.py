from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole, enum_values


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=enum_values,
        ),
        default=UserRole.STUDENT,
        nullable=False,
    )
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    institution: Mapped["Institution | None"] = relationship(back_populates="users")
    uploaded_documents: Mapped[list["UploadedDocument"]] = relationship(
        back_populates="uploader"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    assigned_reviews: Mapped[list["ManualReview"]] = relationship(back_populates="reviewer")
    batch_verifications: Mapped[list["BatchVerification"]] = relationship(back_populates="uploader")
    candidate_profiles: Mapped[list["CandidateProfile"]] = relationship(back_populates="creator")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    owned_workspaces: Mapped[list["Workspace"]] = relationship(back_populates="owner")
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")
