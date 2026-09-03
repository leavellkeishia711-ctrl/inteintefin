import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer, DateTime, UniqueConstraint, CheckConstraint, Index
from datetime import datetime
from app.db.session import Base
from .base import TimestampMixin, CompanyScoped, SoftDeleteMixin

class ConnectorConfig(Base, TimestampMixin, CompanyScoped, SoftDeleteMixin):
    __tablename__ = "connector_configs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    connector_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default='active', nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(String, nullable=False)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    last_attempted_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "connector_name", name="uix_company_connector"),
        CheckConstraint("status IN ('active', 'paused', 'failing', 'unauthorized')", name="check_connector_status"),
        Index("ix_connector_configs_next_sync", "status", "next_sync_at"),
    )
