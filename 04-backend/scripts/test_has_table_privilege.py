import psycopg2
conn = psycopg2.connect('postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')
cur = conn.cursor()
for i in range(20):
    cur.execute("SELECT has_table_privilege('app_user', 'users', 'SELECT')")
    print(f"{i}: {cur.fetchone()}")
print('Done!')
