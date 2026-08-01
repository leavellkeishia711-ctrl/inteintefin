import asyncio, psycopg, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
async def main():
    DSN = "postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        res = await conn.execute("SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid = 'users'::regclass")
        for r in await res.fetchall(): print(r)
        print("-- policies --")
        res2 = await conn.execute("SELECT polname, polcmd, polqual, polwithcheck FROM pg_policy WHERE polrelid = 'users'::regclass")
        for r in await res2.fetchall(): print(r)
asyncio.run(main())
