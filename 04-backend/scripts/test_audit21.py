import os
import asyncio
import asyncpg
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

async def run_test():
    try:
        conn = await asyncpg.connect(url)
        
        # Get company_id
        company_id = await conn.fetchval("SELECT id FROM companies LIMIT 1")
        
        async with conn.transaction():
            print("Transaction started")
            await conn.execute("SELECT set_config('app.company_id', $1, true)", str(company_id))
            print("set_config done")
            
            print("Inserting into dummy2...")
            await conn.execute("INSERT INTO dummy2 (id) VALUES ($1)", str(uuid.uuid4()))
            print("Insert succeeded!")
            
        print("Commit succeeded!")
        await conn.close()
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(run_test())
