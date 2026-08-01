import asyncio
import sys
from sqlalchemy import text
from app.db.session import engine

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE POLICY tenant_isolation ON users USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid)"))
    print("Policy restored")
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
