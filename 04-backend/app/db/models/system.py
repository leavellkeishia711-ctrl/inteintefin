import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, CHAR, ForeignKey, Date, Numeric, DateTime, JSON, Integer, CheckConstraint, Index
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from decimal import Decimal
from datetime import date, datetime
from app.db.session import Base
from .base import TimestampMixin, SoftDeleteMixin, CompanyScoped
from sqlalchemy.dialects.postgresql import INET, JSONB

class AffiliateNetwork(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "affiliate_networks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    payment_terms: Mapped[str] = mapped_column(String, nullable=False)
    payout_model: Mapped[str] = mapped_column(String, nullable=False)
    typical_hold_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)

    __table_args__ = (
        CheckConstraint("payment_terms IN ('net7', 'net15', 'net30', 'net60', 'weekly', 'biweekly')", name="check_aff_net_payment_terms"),
        CheckConstraint("payout_model IN ('cpa', 'cpl', 'revshare', 'hybrid')", name="check_aff_net_payout_model"),
    )

class PartnerPayout(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "partner_payouts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    network_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("affiliate_networks.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=False)
    scrubbed_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    booked_on: Mapped[date] = mapped_column(Date, nullable=False)
    hold_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('booked', 'in_hold', 'scrubbed', 'paid')", name="check_partner_payout_status"),
        Index("ix_partner_payouts_company_status_hold", "company_id", "status", "hold_until"),
    )

class Alert(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "alerts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String, nullable=False)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("type IN ('financial', 'operational', 'security')", name="check_alert_type"),
        CheckConstraint("risk_level IN ('info', 'warning', 'critical')", name="check_alert_risk_level"),
        Index("ix_alerts_company_unacked", "company_id", postgresql_where=sa.text("acknowledged_at IS NULL")),
        Index("ix_alerts_dedup_key", "dedup_key"),
    )

class AuditLog(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String, default='user', nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    diff: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'system')", name="check_audit_actor_type"),
        Index("ix_audit_log_company_entity", "company_id", "entity_type", "entity_id"),
    )

class CompensationPlan(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "compensation_plans"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    bonus_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2, asdecimal=True), default=Decimal(0), nullable=False)
    bonus_basis: Mapped[str] = mapped_column(String, nullable=False)
    quota_target: Mapped[Decimal | None] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=True)
    rate_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=True)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        ExcludeConstraint(
            ("company_id", "="),
            ("user_id", "="),
            (sa.text("daterange(effective_from, COALESCE(effective_to, 'infinity'), '[]')"), "&&"),
            name="excl_comp_plan_overlap",
            where=sa.text("deleted_at IS NULL")
        ),
        CheckConstraint("effective_to IS NULL OR effective_from <= effective_to", name="check_comp_plan_dates"),
    )

class PayrollRun(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "payroll_runs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'paid')", name="check_payroll_run_status"),
        CheckConstraint("period_start <= period_end", name="check_payroll_run_dates"),
    )

class PayrollLineItem(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "payroll_line_items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payroll_runs.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), default=Decimal(0), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default='draft', nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'paid', 'held')", name="check_payroll_line_item_status"),
    )

class DecisionRecommendation(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "decision_recommendations"
    recommendation_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    vertical: Mapped[str | None] = mapped_column(String, nullable=True)
    geo: Mapped[str | None] = mapped_column(String, nullable=True)
    field: Mapped[str] = mapped_column(String, nullable=False)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=True)
    recommended_value: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=False)
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 2, asdecimal=True), nullable=True)
    reasoning: Mapped[str] = mapped_column(String, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2, asdecimal=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default='recommended', nullable=False)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('recommended', 'approved', 'executed', 'rejected')", name="check_decision_status"),
        CheckConstraint("type IN ('budget_shift', 'stop_loss', 'scale_up', 'payout_discrepancy')", name="check_decision_type"),
    )

class ChatMessage(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "chat_messages"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    tool_calls_used: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="check_chat_message_role"),
    )
