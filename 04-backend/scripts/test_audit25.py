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
    
    print("Creating temp table...")
    cur.execute("CREATE TEMP TABLE IF NOT EXISTS _ctx (company_id uuid)")
    cur.execute("TRUNCATE _ctx")
    cur.execute("INSERT INTO _ctx VALUES (%s)", (str(company_id),))
    
    # Check if we can select from it
    cur.execute("SELECT company_id FROM _ctx LIMIT 1")
    print(f"Context company_id: {cur.fetchone()[0]}")
    
    print("Inserting into dummy2...")
    cur.execute("INSERT INTO dummy2 (id) VALUES (%s)", (str(uuid.uuid4()),))
    print("Insert succeeded!")
    
    conn.commit()
    print("Commit succeeded!")
except Exception as e:
    print(f"Failed: {e}")
