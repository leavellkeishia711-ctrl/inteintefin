import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT relation::regclass, mode, granted, pid FROM pg_locks WHERE relation::regclass::text IN ('companies', 'users', 'audit_log')")
print("Locks:")
for row in cur.fetchall():
    print(row)
