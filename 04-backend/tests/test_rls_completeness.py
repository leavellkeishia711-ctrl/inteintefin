import pytest
from sqlalchemy import text
from app.db.session import engine

def test_all_tables_have_rls():
    """
    Check 2: Ensure no domain table is missing Row-Level Security.
    Queries pg_class to ensure all tables in the 'public' schema have RLS enabled (relrowsecurity)
    and that RLS is forced (relforcerowsecurity).
    Alembic migrations (alembic_version) are exempt.
    """
    import psycopg2
    import os
    from dotenv import load_dotenv
    load_dotenv()
    url = str(os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/financeintel").replace("postgresql+asyncpg", "postgresql").replace("postgresql+psycopg", "postgresql").replace("?sslmode=require", "").replace("&sslmode=require", "").replace("?ssl=require", "").replace("&ssl=require", "")
    
    sslmode = os.getenv("DB_SSLMODE", "require")
    conn = psycopg2.connect(url, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY 1;
    """)
    tables = cursor.fetchall()
    conn.close()

    failing_tables = []
    for relname, relrowsecurity, relforcerowsecurity in tables:
        if relname == "alembic_version":
            continue
        if not relrowsecurity or not relforcerowsecurity:
            failing_tables.append(relname)

    assert not failing_tables, f"The following tables are missing RLS or force-RLS: {failing_tables}"

