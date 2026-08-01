import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)
cur = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'ad_accounts'")
for row in cur.fetchall():
    print(row)
