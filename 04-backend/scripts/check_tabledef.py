import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT pg_get_tabledef('audit_log')")
print(cur.fetchall())
