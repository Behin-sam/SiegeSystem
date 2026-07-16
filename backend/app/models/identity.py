"""
ORM models for Federated Identity module: Identity, IdentityVerificationHistory, and IdentitySignal.
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Identity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "identity"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="identity")
    verification_history: Mapped[list["IdentityVerificationHistory"]] = relationship(
        "IdentityVerificationHistory", back_populates="identity", cascade="all, delete-orphan"
    )
    signals: Mapped[list["IdentitySignal"]] = relationship(
        "IdentitySignal", back_populates="identity", cascade="all, delete-orphan"
    )


class IdentityVerificationHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "identity_verification_history"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    identity: Mapped["Identity"] = relationship("Identity", back_populates="verification_history")


class IdentitySignal(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "identity_signals"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signal_key: Mapped[str] = mapped_column(String(100), nullable=False)
    signal_value: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    identity: Mapped["Identity"] = relationship("Identity", back_populates="signals")
