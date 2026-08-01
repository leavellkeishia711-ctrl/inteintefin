import os, psycopg2
from app.core.config import settings

url = str(settings.DATABASE_URL).replace('postgresql+asyncpg', 'postgresql').replace('postgresql+psycopg', 'postgresql').replace('?ssl=require', '?sslmode=require')
print(f"Connecting to {url}")
try:
    conn = psycopg2.connect(url, sslmode='require')
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pid, state, query 
        FROM pg_stat_activity 
        WHERE datname = 'postgres' 
        AND usename = 'postgres.dkgkilpqaigmviyhfmuh';
    """)
    rows = cursor.fetchall()
    print(f"Active connections: {len(rows)}")
    for row in rows:
        print(row)
    conn.close()
except Exception as e:
    print('Failed:', type(e).__name__, e)
