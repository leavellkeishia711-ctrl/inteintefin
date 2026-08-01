import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename IN ('postgres', 'app_user') AND pid <> pg_backend_pid()")
print(cur.fetchall())
