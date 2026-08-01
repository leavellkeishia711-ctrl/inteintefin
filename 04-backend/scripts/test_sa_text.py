"""
Test: SQLAlchemy ORM INSERT into users.
With echo=True to see the exact SQL.
"""
import asyncio
import uuid
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, event
from sqlalchemy.pool import NullPool
from sqlalchemy.dialects.postgresql.psycopg import PGDialectAsync_psycopg

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
    echo=True,  # Verbose SQL logging
    poolclass=NullPool,
    connect_args={"prepare_threshold": None},
)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with async_session_maker() as session:
        async with session.begin():
            # Setup tenant context
            await session.execute(text("SET LOCAL ROLE app_user"))
            await session.execute(
                text("SELECT set_config('app.company_id', :cid, true)"),
                {"cid": str(company_id)}
            )
            
            # Insert company
            await session.execute(text(
                "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
            ), {"id": company_id, "name": "SA_Test", "currency": "USD"})
            
            print("\n>>> About to execute INSERT INTO users with ORM-style text <<<")
            
            # This mimics what SQLAlchemy ORM generates
            # The key question: does psycopg dialect add ::TYPE casts?
            await session.execute(text(
                """INSERT INTO users (id, company_id, name, email, password_hash, role) 
                VALUES (:id, :company_id, :name, :email, :password_hash, :role)
                RETURNING users.created_at, users.updated_at"""
            ), {
                "id": user_id,
                "company_id": company_id,
                "name": "TestUser",
                "email": "test@sa.com",
                "password_hash": "hash123",
                "role": "owner",
            })
            print(">>> INSERT succeeded <<<")
    
    print("Session closed successfully")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
