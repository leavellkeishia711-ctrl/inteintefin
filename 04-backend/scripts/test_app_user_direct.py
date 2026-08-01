"""
1. Check if app_user role exists and has LOGIN
2. Grant LOGIN + password to app_user
3. Try connecting as app_user through Supavisor
4. Test full flow as app_user (RLS should work automatically)
"""
import asyncio, psycopg, sys, uuid
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DSN_POSTGRES = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'

async def step1_check_app_user():
    print('=== Step 1: Check app_user role ===')
    async with await psycopg.AsyncConnection.connect(DSN_POSTGRES, prepare_threshold=None) as conn:
        r = await conn.execute("SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname = 'app_user'")
        row = await r.fetchone()
        if row:
            print(f'  app_user exists: login={row[1]}, super={row[2]}')
        else:
            print('  app_user does NOT exist')
        await conn.commit()
        return row

async def step2_grant_login():
    print('\n=== Step 2: Grant LOGIN to app_user ===')
    async with await psycopg.AsyncConnection.connect(DSN_POSTGRES, prepare_threshold=None) as conn:
        await conn.execute("ALTER ROLE app_user WITH LOGIN PASSWORD 'AppUser_Fin2024!'")
        await conn.commit()
        print('  OK: LOGIN granted with password')

async def step3_connect_as_app_user():
    print('\n=== Step 3: Connect as app_user via Supavisor ===')
    # Supavisor format: user.project-ref
    DSN_APP = 'postgresql://app_user.dkgkilpqaigmviyhfmuh:AppUser_Fin2024!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'
    try:
        async with await psycopg.AsyncConnection.connect(DSN_APP, prepare_threshold=None) as conn:
            r = await conn.execute('SELECT current_user, session_user')
            row = await r.fetchone()
            print(f'  Connected! current_user={row[0]}, session_user={row[1]}')
            await conn.commit()
            return True
    except Exception as e:
        print(f'  FAILED: {type(e).__name__}: {e}')
        return False

async def step4_full_flow_as_app_user():
    print('\n=== Step 4: Full flow as app_user (RLS active) ===')
    DSN_APP = 'postgresql://app_user.dkgkilpqaigmviyhfmuh:AppUser_Fin2024!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'
    async with await psycopg.AsyncConnection.connect(DSN_APP, prepare_threshold=None) as conn:
        c_id = str(uuid.uuid4())
        u_id = str(uuid.uuid4())
        t_id = str(uuid.uuid4())
        
        # Set tenant context
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        print('  set_config: OK')
        
        # Insert company
        await conn.execute(
            'INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)',
            (c_id, 'TestCo', 'USD', False, 'en')
        )
        print('  INSERT company: OK')
        
        # Insert user
        await conn.execute(
            'INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)',
            (u_id, c_id, 'TestUser', f'{u_id}@test.com', 'hash', 'owner')
        )
        print('  INSERT user: OK')
        
        # Insert team
        await conn.execute(
            'INSERT INTO teams (id, company_id, name) VALUES (%s, %s, %s)',
            (t_id, c_id, 'DefaultTeam')
        )
        print('  INSERT team: OK')
        
        await conn.commit()
        print('  COMMIT: OK')
        
        # Verify RLS
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        r = await conn.execute('SELECT count(*) FROM companies')
        count = (await r.fetchone())[0]
        print(f'  Companies visible (own tenant): {count}')
        
        fake = str(uuid.uuid4())
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (fake,))
        r = await conn.execute('SELECT count(*) FROM companies')
        count2 = (await r.fetchone())[0]
        print(f'  Companies visible (other tenant): {count2}')
        print(f'  RLS isolation works: {count == 1 and count2 == 0}')
        await conn.commit()

async def main():
    row = await step1_check_app_user()
    if not row or not row[1]:
        await step2_grant_login()
    ok = await step3_connect_as_app_user()
    if ok:
        await step4_full_flow_as_app_user()

asyncio.run(main())
