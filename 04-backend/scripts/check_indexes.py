import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'audit_log'")
print("Indexes on audit_log:")
for row in cur.fetchall():
    print(row)
