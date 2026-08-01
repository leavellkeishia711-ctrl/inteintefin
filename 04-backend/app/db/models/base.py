from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from sqlalchemy import func, DateTime
from datetime import datetime
from app.db.session import Base
import uuid

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class CompanyScoped:
    # All domain tables must inherit this to enforce multitenancy
    # The actual RLS policies are applied at the database level.
    # At the application level, we also include it in the ORM to ensure it's written.
    @declared_attr
    def company_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(nullable=False)
