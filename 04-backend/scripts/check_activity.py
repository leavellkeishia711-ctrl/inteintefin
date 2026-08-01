import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT pid, usename, state, query FROM pg_stat_activity WHERE datname = current_database() AND state != 'idle'")
print(cur.fetchall())
