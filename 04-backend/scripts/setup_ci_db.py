import asyncio
import asyncpg
import time
import sys

async def connect_with_retry():
    max_retries = 30
    for i in range(max_retries):
        try:
            conn = await asyncpg.connect("postgresql://fi:fi@localhost:5432/financeintel", timeout=10)
            return conn
        except Exception as e:
            print(f"Waiting for Postgres... ({i+1}/{max_retries}): {e}")
            await asyncio.sleep(1)
    raise RuntimeError("Could not connect to Postgres after 30 retries")

async def main():
    conn = await connect_with_retry()
    try:
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
                    CREATE ROLE app_user WITH LOGIN PASSWORD 'app';
                END IF;
            END $$;
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
            GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
        """)
        print("Successfully provisioned app_user role and permissions for CI")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
