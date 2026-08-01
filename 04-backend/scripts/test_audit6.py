import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY")
print("Disabled RLS on audit_log")
