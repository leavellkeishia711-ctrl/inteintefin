import sys
import asyncio

# psycopg requires WindowsSelectorEventLoopPolicy on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import sqlalchemy
from contextlib import asynccontextmanager
from app.core.config import settings
from typing import AsyncGenerator

import uuid
from sqlalchemy.pool import NullPool
from contextvars import ContextVar

# ContextVar for Defense-in-Depth RLS
current_company_id: ContextVar[str | None] = ContextVar("current_company_id", default=None)

# Configure connection args based on DB_POOLER_MODE
connect_args = {}
if settings.DB_SSLMODE and settings.DB_SSLMODE != "disable":
    connect_args["ssl"] = settings.DB_SSLMODE

if settings.DB_POOLER_MODE:
    connect_args.update({
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: str(uuid.uuid4()),
    })

engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.ECHO_SQL,
    poolclass=NullPool if settings.DB_POOLER_MODE else None,
    connect_args=connect_args
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

tenant_engine = engine
if settings.APP_USER_DATABASE_URL:
    tenant_engine = create_async_engine(
        str(settings.APP_USER_DATABASE_URL),
        echo=settings.ECHO_SQL,
        poolclass=NullPool if settings.DB_POOLER_MODE else None,
        connect_args=connect_args
    )

tenant_session_maker = async_sessionmaker(
    tenant_engine, class_=AsyncSession, expire_on_commit=False
)

from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm import with_loader_criteria

@event.listens_for(Session, "do_orm_execute")
def _do_orm_execute(execute_state):
    # This acts as a defense-in-depth layer for ORM queries.
    # NOTE: with_loader_criteria does NOT cover bulk update/delete or raw SQL.
    # Postgres RLS is the ONLY true boundary of isolation.
    if execute_state.session.info.get("is_tenant_session"):
        if execute_state.is_select or execute_state.is_update or execute_state.is_delete:
            cid = current_company_id.get()
            if cid is None:
                raise RuntimeError("ORM layer error: current_company_id ContextVar is not set in tenant_session.")
            
            # Cast to UUID for correct type comparison with the UUID column
            cid_uuid = uuid.UUID(cid) if isinstance(cid, str) else cid
            
            # We must import lazily to avoid circular imports
            from app.db.models.base import CompanyScoped
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    CompanyScoped,
                    lambda cls: cls.company_id == cid_uuid,
                    include_aliases=True
                )
            )

class Base(DeclarativeBase):
    pass

@asynccontextmanager
async def system_session() -> AsyncGenerator[AsyncSession, None]:
    """A session that retains the postgres superuser role. Use ONLY for pre-auth lookups."""
    async with async_session_maker() as session:
        yield session

@asynccontextmanager
async def tenant_session(company_id: str) -> AsyncGenerator[AsyncSession, None]:
    token = current_company_id.set(str(company_id))
    try:
        async with tenant_session_maker() as session:
            session.info["is_tenant_session"] = True
            try:
                async with session.begin():
                    await session.execute(
                        text("SELECT set_config('app.company_id', :cid, true)"),
                        {"cid": str(company_id)},
                    )
                    yield session
            except sqlalchemy.exc.InvalidRequestError as e:
                if "Can't operate on closed transaction inside context manager" in str(e):
                    pass
                else:
                    raise
    finally:
        current_company_id.reset(token)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        async with session.begin():
            yield session

