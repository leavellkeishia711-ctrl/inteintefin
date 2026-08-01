"""
Minimal test: can we do 3 INSERTs into different tables in one connection?
No SET ROLE, no set_config, pure postgres.
Run 5 times to check consistency.
"""
import asyncio, psycopg, sys, uuid, time
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DSN = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'

async def single_run(i):
    try:
        async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
            c_id = str(uuid.uuid4())
            u_id = str(uuid.uuid4())
            t_id = str(uuid.uuid4())
            await conn.execute(
                'INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)',
                (c_id, 'Test', 'USD', False, 'en')
            )
            await conn.execute(
                'INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)',
                (u_id, c_id, 'U', f'{u_id}@t.com', 'hash', 'owner')
            )
            await conn.execute(
                'INSERT INTO teams (id, company_id, name) VALUES (%s, %s, %s)',
                (t_id, c_id, 'Team')
            )
            await conn.commit()
            print(f'  Run {i}: OK (3 inserts + commit)')
    except Exception as e:
        print(f'  Run {i}: FAIL ({type(e).__name__}: {str(e)[:80]})')

async def main():
    print('=== 5 sequential runs, no SET ROLE, 3 INSERTs each ===')
    for i in range(1, 6):
        await single_run(i)
        await asyncio.sleep(1)  # gap between runs

asyncio.run(main())
