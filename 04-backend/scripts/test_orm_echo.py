"""
Test: SQLAlchemy ORM session.add(User(...)) with echo=True.
Uses a fresh engine to avoid import side-effects.
"""
import asyncio
import uuid
import sys
import logging

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format='%(message)s')

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, String, Boolean, BigInteger, ForeignKey, DateTime, func, event
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.pool import NullPool
from sqlalchemy.dialects.postgresql.psycopg import PGDialectAsync_psycopg
from datetime import datetime

# Apply the same monkey-patch as session.py
def _patched_initialize(self, connection):
    self.default_schema_name = "public"
    self.default_isolation_level = "READ COMMITTED"
    self._backslash_escapes = False
    self.server_version_info = (15, 6)
    self.implicit_returning = True
    self.supports_native_enum = True
    self.supports_smallserial = True
    self.supports_sequences = True
    self.sequences_optional = True
    self._supports_create_index_concurrently = True
    self._supports_drop_index_concurrently = True
    self.supports_identity_columns = True
    self.supports_comments = True
    self._json_deserializer = None
    self._json_serializer = None

PGDialectAsync_psycopg.initialize = _patched_initialize

DSN = "postgresql+psycopg://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"

engine = create_async_engine(
    DSN,
    echo=True,
    poolclass=NullPool,
    connect_args={"prepare_threshold": None},
)

# Intercept the raw DBAPI cursor to see EXACTLY what psycopg sends
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    print(f"\n{'='*60}")
    print(f"RAW SQL: {statement}")
    print(f"RAW PARAMS: {parameters}")
    print(f"{'='*60}\n")

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    preferred_language: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

async def main():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    print(f"Company ID: {company_id}")
    print(f"User ID: {user_id}")
    
    async with async_session_maker() as session:
        async with session.begin():
            await session.execute(text("SET LOCAL ROLE app_user"))
            await session.execute(
                text("SELECT set_config('app.company_id', :cid, true)"),
                {"cid": str(company_id)}
            )
            
            await session.execute(text(
                "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
            ), {"id": company_id, "name": "ORM_Test", "currency": "USD"})
            
            user = User(
                id=user_id,
                company_id=company_id,
                name="ORMUser",
                email="orm@test.com",
                password_hash="hash789",
                role="owner",
            )
            session.add(user)
            print("\n>>> FLUSHING ORM USER <<<")
            await session.flush()
            print(f">>> FLUSH OK, created_at={user.created_at} <<<")
    
    print("Session closed successfully")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
