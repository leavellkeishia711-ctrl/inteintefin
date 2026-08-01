"""
Stress test: 5 runs as app_user directly (no SET ROLE), 3 INSERTs each.
"""
import asyncio, psycopg, sys, uuid
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DSN = 'postgresql://app_user.dkgkilpqaigmviyhfmuh:AppUser_Fin2024!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'

async def single_run(i):
    try:
        async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
            c_id = str(uuid.uuid4())
            u_id = str(uuid.uuid4())
            t_id = str(uuid.uuid4())
            await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
            await conn.execute(
                'INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)',
                (c_id, f'Test_{i}', 'USD', False, 'en')
            )
            await conn.execute(
                'INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)',
                (u_id, c_id, f'User_{i}', f'{u_id}@t.com', 'hash', 'owner')
            )
            await conn.execute(
                'INSERT INTO teams (id, company_id, name) VALUES (%s, %s, %s)',
                (t_id, c_id, f'Team_{i}')
            )
            await conn.commit()
            # Verify RLS
            await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
            r = await conn.execute('SELECT count(*) FROM companies')
            own = (await r.fetchone())[0]
            await conn.execute("SELECT set_config('app.company_id', %s, true)", (str(uuid.uuid4()),))
            r = await conn.execute('SELECT count(*) FROM companies')
            other = (await r.fetchone())[0]
            await conn.commit()
            rls_ok = own == 1 and other == 0
            print(f'  Run {i}: OK (3 inserts, RLS={rls_ok})')
    except Exception as e:
        print(f'  Run {i}: FAIL ({type(e).__name__}: {str(e)[:80]})')

async def main():
    print('=== Stress test: app_user direct, 5 runs ===')
    for i in range(1, 6):
        await single_run(i)
        await asyncio.sleep(0.5)

asyncio.run(main())
