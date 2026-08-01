"""
Diagnostic: isolate whether Supavisor kills connection after N statements
or if it's table-specific. Tests on port 6543 (transaction mode).
"""
import asyncio, psycopg, sys, uuid
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DSN = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'

async def test_selects_only():
    """Test: can we run many SELECTs after SET LOCAL ROLE?"""
    print('\n=== TEST 1: Multiple SELECTs after SET LOCAL ROLE ===')
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        await conn.execute('SET LOCAL ROLE app_user')
        c_id = str(uuid.uuid4())
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        for i in range(5):
            r = await conn.execute('SELECT 1')
            print(f'  SELECT {i+1}: OK')
        await conn.commit()
        print('  COMMIT: OK')

async def test_two_company_inserts():
    """Test: can we INSERT into companies twice?"""
    print('\n=== TEST 2: Two INSERTs into companies ===')
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        await conn.execute('SET LOCAL ROLE app_user')
        c_id1 = str(uuid.uuid4())
        c_id2 = str(uuid.uuid4())
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id1,))
        await conn.execute('INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)', (c_id1, 'Test1', 'USD', False, 'en'))
        print('  Company 1: OK')
        # Now change tenant context and insert second company
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id2,))
        await conn.execute('INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)', (c_id2, 'Test2', 'USD', False, 'en'))
        print('  Company 2: OK')
        await conn.commit()
        print('  COMMIT: OK')

async def test_no_set_role():
    """Test: INSERT into users WITHOUT SET LOCAL ROLE (as postgres, RLS bypassed)"""
    print('\n=== TEST 3: Company + User WITHOUT SET LOCAL ROLE ===')
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        c_id = str(uuid.uuid4())
        u_id = str(uuid.uuid4())
        await conn.execute('INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)', (c_id, 'Test', 'USD', False, 'en'))
        print('  Company: OK')
        await conn.execute('INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)', (u_id, c_id, 'U', f'{u_id}@test.com', 'hash', 'owner'))
        print('  User: OK')
        await conn.commit()
        print('  COMMIT: OK')

async def test_separate_connections():
    """Test: Company in conn1, User in conn2"""
    print('\n=== TEST 4: Separate connections ===')
    c_id = str(uuid.uuid4())
    u_id = str(uuid.uuid4())
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        await conn.execute('SET LOCAL ROLE app_user')
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        await conn.execute('INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)', (c_id, 'Test', 'USD', False, 'en'))
        await conn.commit()
        print('  Company (conn1): OK')
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        await conn.execute('SET LOCAL ROLE app_user')
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        await conn.execute('INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)', (u_id, c_id, 'U', f'{u_id}@test.com', 'hash', 'owner'))
        await conn.commit()
        print('  User (conn2): OK')

async def main():
    tests = [test_selects_only, test_two_company_inserts, test_no_set_role, test_separate_connections]
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f'  FAILED: {type(e).__name__}: {e}')

asyncio.run(main())
