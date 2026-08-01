import os
import psycopg
import uuid
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
                # get a valid company and user
                await cur.execute("SELECT id FROM companies LIMIT 1")
                res = await cur.fetchone()
                if not res:
                    print("No companies")
                    return
                company_id = res[0]
                
                await cur.execute("SELECT id FROM users LIMIT 1")
                res = await cur.fetchone()
                user_id = res[0] if res else None

                print(f"Testing insert for company {company_id}, user {user_id}")
                
                await cur.execute("BEGIN")
                await cur.execute("SELECT set_config('app.company_id', %s, true)", (str(company_id),))

                await cur.execute(
                    "INSERT INTO audit_log (id, company_id, actor_user_id, entity_type, entity_id, action, diff, request_id, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (uuid.uuid4(), company_id, user_id, "transaction", uuid.uuid4(), "create", '{"status": "created"}', None, None, None)
                )
                print("Insert succeeded!")
                await cur.execute("COMMIT")
                print("Commit succeeded!")
            except Exception as e:
                print(f"Insert failed: {e}")

asyncio.run(main())
