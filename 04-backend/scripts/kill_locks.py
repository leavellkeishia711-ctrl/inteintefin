import psycopg2
c = psycopg2.connect('postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')
c.autocommit = True
cur = c.cursor()
cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid != pg_backend_pid() AND datname = 'postgres'")
print(cur.fetchall())
