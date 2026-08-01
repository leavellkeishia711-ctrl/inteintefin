import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT tgname, tgfoid::regproc FROM pg_trigger WHERE tgrelid = 'audit_log'::regclass")
for row in cur.fetchall():
    print(row)
