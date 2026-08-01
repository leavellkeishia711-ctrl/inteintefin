import os, psycopg2
from app.core.config import settings
url = str(settings.DATABASE_URL).replace('postgresql+asyncpg', 'postgresql').replace('postgresql+psycopg', 'postgresql').replace('5432', '6543').replace('?ssl=require', '').replace('?sslmode=require', '').replace('&sslmode=require', '')
try:
    conn = psycopg2.connect(url, sslmode='require')
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = 'postgres' 
        AND usename = 'postgres.dkgkilpqaigmviyhfmuh'
        AND pid <> pg_backend_pid()
        AND state in ('idle', 'idle in transaction', 'idle in transaction (aborted)');
    """)
    print('Terminated backends.')
    conn.close()
except Exception as e:
    print('Failed:', e)
