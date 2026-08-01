import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, CHAR, Numeric
from decimal import Decimal
from app.db.session import Base
from .base import TimestampMixin, SoftDeleteMixin

class Company(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    base_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    budget_requests_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_language: Mapped[str] = mapped_column(String, default='en', nullable=False)
    alert_runway_threshold_days: Mapped[int] = mapped_column(default=30, server_default='30', nullable=False)
    alert_roi_threshold: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal('0'), server_default='0', nullable=False)
    alert_stalled_data_days: Mapped[int] = mapped_column(default=3, server_default='3', nullable=False)

