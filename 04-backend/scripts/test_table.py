import asyncio, psycopg, sys, uuid
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def main():
    DSN = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        print('Connected as postgres')
        await conn.execute("CREATE TABLE IF NOT EXISTS test_table (id UUID PRIMARY KEY, company_id UUID NOT NULL, name TEXT)")
        await conn.execute("ALTER TABLE test_table ENABLE ROW LEVEL SECURITY")
        await conn.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT FROM pg_policies WHERE policyname = 'tenant_isolation' AND tablename = 'test_table') THEN
                    CREATE POLICY "tenant_isolation" ON test_table FOR ALL TO app_user
                    USING (company_id = (current_setting('app.company_id'))::uuid)
                    WITH CHECK (company_id = (current_setting('app.company_id'))::uuid);
                END IF;
            END $$;
        """)
        await conn.execute("GRANT ALL PRIVILEGES ON test_table TO app_user")
        
        await conn.execute('SET LOCAL ROLE app_user')
        c_id = str(uuid.uuid4())
        await conn.execute("SELECT set_config('app.company_id', %s, true)", (c_id,))
        print('Inserting into test_table as app_user')
        try:
            await conn.execute("INSERT INTO test_table (id, company_id, name) VALUES (%s, %s, 'Test')", (str(uuid.uuid4()), c_id))
            print('Insert OK')
        except Exception as e:
            print('Insert error:', e)
        await conn.commit()
asyncio.run(main())
