import uuid
from sqlalchemy.orm import Mapped, mapped_column
import sqlalchemy as sa
from sqlalchemy import String, Boolean, CHAR, BigInteger, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import CITEXT
from datetime import datetime
from app.db.session import Base
from .base import TimestampMixin, SoftDeleteMixin, CompanyScoped

class User(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    preferred_language: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uix_company_email", "company_id", "email", unique=True, postgresql_where=sa.text("deleted_at IS NULL")),
        CheckConstraint("role IN ('owner','cfo','team_lead','media_buyer','farmer','processor','creative','admin')", name="check_user_role"),
    )

class Team(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "teams"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    lead_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

class TelegramLinkToken(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "telegram_link_tokens"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="check_expires_at_after_created_at"),
        Index("ix_telegram_link_tokens_user_expires", "user_id", "expires_at"),
    )

class Invite(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "invites"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('owner','cfo','team_lead','media_buyer','farmer','processor','creative','admin')", name="check_invite_role"),
        Index("ix_invites_company_email", "company_id", "email"),
        Index("ix_invites_email_expires", "email", "expires_at", postgresql_where=accepted_at.is_(None)),
    )
