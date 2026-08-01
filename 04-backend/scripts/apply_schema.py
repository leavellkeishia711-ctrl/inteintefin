import psycopg2
import sys

try:
    with open('init_schema.sql', 'r', encoding='utf-8') as f:
        sql = f.read()

    # Apply some basic fixes because create_mock_engine prints without true compilation for types sometimes,
    # but let's just try running it directly first.
    c = psycopg2.connect('postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require')
    c.autocommit = True
    cur = c.cursor()
    cur.execute(sql)
    print("Schema created successfully!")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
