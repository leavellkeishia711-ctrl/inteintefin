import os
import psycopg
import asyncio
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    async with await psycopg.AsyncConnection.connect(url) as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("BEGIN")
                await cur.execute("SELECT set_config('app.company_id', '00000000-0000-0000-0000-000000000000', true)")
                print("Config set.")
                await cur.execute("COMMIT")
                print("Commit succeeded!")
            except Exception as e:
                print(f"Failed: {e}")

asyncio.run(main())
