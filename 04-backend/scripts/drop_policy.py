import asyncio
import sys
from sqlalchemy import text
from app.db.session import engine

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("DROP POLICY IF EXISTS tenant_isolation ON users"))
    print("Policy dropped")
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
