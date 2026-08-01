import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, CHAR, ForeignKey, Date, Numeric, Integer, DateTime, CheckConstraint, Index
import sqlalchemy as sa
from decimal import Decimal
from datetime import date, datetime
from app.db.session import Base
from .base import TimestampMixin, SoftDeleteMixin, CompanyScoped

class FxRate(Base, TimestampMixin):
    __tablename__ = "fx_rates"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("rate > 0", name="check_fx_rate_positive"),
        CheckConstraint("from_currency <> to_currency", name="check_fx_rate_different_currencies"),
        sa.UniqueConstraint("rate_date", "from_currency", "to_currency", "source", name="uq_fx_rate_date_currencies_source"),
    )

class ImportBatch(Base, TimestampMixin, CompanyScoped):
    __tablename__ = "import_batches"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("row_count >= 0", name="check_import_batch_row_count"),
        CheckConstraint("error_count >= 0", name="check_import_batch_error_count"),
        CheckConstraint(
            "status IN ('pending','processing','completed','completed_with_errors','failed','rolled_back')",
            name="check_import_batch_status"
        ),
        Index("ix_import_batches_company_created", "company_id", "created_at"),
    )

class Transaction(Base, TimestampMixin, SoftDeleteMixin, CompanyScoped):
    __tablename__ = "transactions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4, asdecimal=True), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default='manual', nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        sa.Index(
            "uix_company_source_external", 
            "company_id", "source", "external_id", 
            unique=True, 
            postgresql_where=sa.text("external_id IS NOT NULL")
        ),
        Index("ix_transactions_company_occurred_on", "company_id", "occurred_on"),
        Index("ix_transactions_company_type_category", "company_id", "type", "category"),
        CheckConstraint("type IN ('income', 'expense')", name="check_transaction_type"),
        CheckConstraint(
            "category IN ('ad_spend', 'salary', 'infra', 'tax', 'payout_incoming', 'payout_outgoing', 'consumables', 'depreciation', 'interest', 'other')",
            name="check_transaction_category"
        ),
    )
