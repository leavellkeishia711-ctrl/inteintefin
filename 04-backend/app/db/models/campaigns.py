import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, CHAR, ForeignKey, Date, Numeric, DateTime, UniqueConstraint, CheckConstraint, Index
import sqlalchemy as sa
from decimal import Decimal
from datetime import date, datetime
from app.db.session import Base
from .base import TimestampMixin, SoftDeleteMixin, CompanyScoped

class AdAccount(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "ad_accounts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    prepared_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_buyer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    vertical: Mapped[str | None] = mapped_column(String, nullable=True)
    geo: Mapped[str | None] = mapped_column(String, nullable=True)
    banned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'warming', 'banned', 'suspended')", name="check_ad_account_status"),
        sa.Index(
            "uix_company_platform_external_account",
            "company_id", "platform", "external_account_id",
            unique=True,
            postgresql_where=sa.text("external_account_id IS NOT NULL AND deleted_at IS NULL")
        ),
    )

class Campaign(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "campaigns"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    ad_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ad_accounts.id"), nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    platform: Mapped[str | None] = mapped_column(String, nullable=True)
    geo: Mapped[str | None] = mapped_column(String, nullable=True)
    vertical: Mapped[str | None] = mapped_column(String, nullable=True)
    funding_status: Mapped[str] = mapped_column(String, default='active', nullable=False)

    __table_args__ = (
        CheckConstraint("funding_status IN ('active', 'paused', 'stopped')", name="check_campaign_funding_status"),
    )

class CampaignRun(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "campaign_runs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    ad_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ad_accounts.id"), nullable=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default='active', nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'stopped', 'banned')", name="check_campaign_run_status"),
        CheckConstraint("ended_at IS NULL OR started_at <= ended_at", name="check_campaign_run_dates"),
    )

class CampaignRunStat(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "campaign_run_stats"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    campaign_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaign_runs.id"), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    spend: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        sa.Index(
            "uq_campaign_run_stats",
            "company_id", "campaign_run_id", "stat_date", "source", "external_id",
            unique=True,
            postgresql_where=sa.text("external_id IS NOT NULL")
        ),
        Index("ix_campaign_run_stats_company_date", "company_id", "stat_date"),
    )

class Consumable(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "consumables"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    ad_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ad_accounts.id"), nullable=True)
    identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    purchased_on: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default='active', nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)

    __table_args__ = (
        CheckConstraint("type IN ('proxy', 'card', 'account_service', 'other')", name="check_consumable_type"),
        CheckConstraint("status IN ('active', 'expired', 'burned')", name="check_consumable_status"),
    )
