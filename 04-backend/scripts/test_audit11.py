import os
import psycopg
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=False)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur.fetchone()[0]
    
    cur.execute("SELECT set_config('app.company_id', %s, true)", (str(company_id),))
    print("set_config done")
    
    cur.execute("INSERT INTO dummy2 (id) VALUES (%s)", (str(uuid.uuid4()),))
    print("Inserted")
    conn.commit()
    print("Committed")
except Exception as e:
    print(f"Failed: {e}")
