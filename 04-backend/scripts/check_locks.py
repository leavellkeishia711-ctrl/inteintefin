import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.cursor()
cur.execute("SELECT pid, mode, granted, relation::regclass FROM pg_locks WHERE relation::regclass::text IN ('companies', 'ad_accounts')")
print(cur.fetchall())
