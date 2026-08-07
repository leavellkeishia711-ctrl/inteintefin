import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://postgres@localhost:5432/postgres')
    await conn.execute("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN 
                CREATE ROLE app_user WITH LOGIN PASSWORD 'test'; 
            END IF; 
        END 
        $$;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
    """)
asyncio.run(test())
