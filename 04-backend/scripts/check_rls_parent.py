import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT polname, polcmd, polqual, polwithcheck FROM pg_policy WHERE polrelid = 'companies'::regclass OR polrelid = 'users'::regclass")
for row in cur.fetchall():
    print(row)
