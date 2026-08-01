import psycopg2

conn = psycopg2.connect('postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')
conn.autocommit = True
cur = conn.cursor()

# Check table privileges for app_user
for table in ['companies', 'users', 'transactions']:
    for priv in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
        cur.execute(f"SELECT has_table_privilege('app_user', '{table}', '{priv}')")
        print(f"  app_user {table} {priv}: {cur.fetchone()[0]}")

# Check RLS status
cur.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename IN ('companies','users','transactions')")
print("\nRLS status:")
for r in cur.fetchall():
    print(f"  {r[0]}: RLS={r[1]}")

# Check RLS policies  
cur.execute("SELECT tablename, policyname, cmd, qual FROM pg_policies WHERE schemaname='public'")
print("\nRLS policies:")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}: cmd={r[2]}, qual={r[3]}")

conn.close()
