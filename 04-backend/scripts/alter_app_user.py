import asyncio, psycopg, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def main():
    DSN = 'postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        print('Connected as postgres')
        await conn.execute("ALTER ROLE app_user WITH LOGIN PASSWORD 'AppUser123!'")
        await conn.commit()
        print('app_user altered')
asyncio.run(main())
