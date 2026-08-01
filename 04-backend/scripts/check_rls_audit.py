import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT relrowsecurity FROM pg_class WHERE relname = 'audit_log'")
for row in cur.fetchall():
    print(row)
