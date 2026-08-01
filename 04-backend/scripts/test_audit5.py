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
                await cur.execute("SELECT id FROM users LIMIT 1")
                res = await cur.fetchone()
                user_id = res[0]
                
                print("Selecting with param...")
                await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                print("Success!")
            except Exception as e:
                print(f"Failed: {e}")

asyncio.run(main())
