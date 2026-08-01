"""
Test the new approach: no SET LOCAL ROLE, just set_config + FORCE RLS.
Postgres superuser bypasses RLS by default, but ALTER TABLE ... FORCE ROW LEVEL SECURITY
makes RLS apply even to table owners.
"""
import asyncio, psycopg, sys, uuid
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DSN = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'

async def test_full_flow_no_set_role():
    """Simulate register flow: company + user + team, no SET ROLE"""
    print('\n=== FULL FLOW: No SET ROLE, only set_config ===')
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        c_id = str(uuid.uuid4())
        u_id = str(uuid.uuid4())
        t_id = str(uuid.uuid4())
        
        # Only set the config var, NO SET LOCAL ROLE
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        print('  set_config: OK')
        
        await conn.execute(
            'INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)',
            (c_id, 'TestCo', 'USD', False, 'en')
        )
        print('  INSERT company: OK')
        
        await conn.execute(
            'INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)',
            (u_id, c_id, 'TestUser', f'{u_id}@test.com', 'hash', 'owner')
        )
        print('  INSERT user: OK')
        
        await conn.execute(
            'INSERT INTO teams (id, company_id, name) VALUES (%s, %s, %s)',
            (t_id, c_id, 'DefaultTeam')
        )
        print('  INSERT team: OK')
        
        # Verify data is there
        r = await conn.execute('SELECT count(*) FROM companies WHERE id = %s', (c_id,))
        count = (await r.fetchone())[0]
        print(f'  SELECT company count: {count}')
        
        r = await conn.execute('SELECT count(*) FROM users WHERE company_id = %s', (c_id,))
        count = (await r.fetchone())[0]
        print(f'  SELECT user count: {count}')
        
        await conn.commit()
        print('  COMMIT: OK')

async def test_tenant_isolation_without_role():
    """Check if RLS still works without SET ROLE (it won't for superuser)"""
    print('\n=== TENANT ISOLATION CHECK (no SET ROLE) ===')
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        # Check current user
        r = await conn.execute('SELECT current_user, session_user')
        row = await r.fetchone()
        print(f'  current_user={row[0]}, session_user={row[1]}')
        
        # Check if we can see ALL companies (superuser bypasses RLS)
        r = await conn.execute('SELECT count(*) FROM companies')
        count = (await r.fetchone())[0]
        print(f'  Total companies visible (no set_config): {count}')
        
        # Now set config and check
        fake_id = str(uuid.uuid4())
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (fake_id,))
        r = await conn.execute('SELECT count(*) FROM companies')
        count2 = (await r.fetchone())[0]
        print(f'  Companies visible (with set_config to random uuid): {count2}')
        print(f'  RLS effective? {count2 < count}')
        await conn.commit()

async def main():
    await test_full_flow_no_set_role()
    await test_tenant_isolation_without_role()

asyncio.run(main())
