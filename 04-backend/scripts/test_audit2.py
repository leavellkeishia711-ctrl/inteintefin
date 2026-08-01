import os
import psycopg
from dotenv import load_dotenv
import asyncio

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    async with await psycopg.AsyncConnection.connect(url) as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("SELECT id FROM companies LIMIT 1")
                res = await cur.fetchone()
                company_id = res[0]
                
                await cur.execute("SELECT set_config('app.company_id', %s, false)", (str(company_id),))
                
                print("Selecting from audit_log...")
                await cur.execute("SELECT * FROM audit_log LIMIT 1")
                print(await cur.fetchall())
            except Exception as e:
                print(f"Failed: {e}")

asyncio.run(main())
