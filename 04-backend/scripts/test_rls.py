import asyncio, psycopg, sys, uuid
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def main():
    DSN = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        print('Connected as postgres')
        await conn.execute('SET LOCAL ROLE app_user')
        c_id = str(uuid.uuid4())
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        print('Inserting company')
        try:
            await conn.execute('INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (%s, %s, %s, %s, %s)', (c_id, 'Test', 'USD', False, 'en'))
            print('Company inserted')
        except Exception as e:
            print('Company error', e)
        print('Inserting user')
        try:
            u_id = str(uuid.uuid4())
            await conn.execute(
                'INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s, %s)',
                (u_id, c_id, 'U', 'u@example.com', 'hash', 'owner')
            )
            print('User inserted')
        except Exception as e:
            print('User error', e)
        await conn.commit()
asyncio.run(main())
