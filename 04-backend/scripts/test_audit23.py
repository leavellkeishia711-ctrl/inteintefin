import os
import psycopg2
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg2.connect(url)
    conn.autocommit = False
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur.fetchone()[0]
    
    print("Setting config...")
    cur.execute("SELECT set_config('app.company_id', %s, true)", (company_id,))
    
    print("Inserting into ad_accounts...")
    cur.execute(
        "INSERT INTO ad_accounts (id, company_id, external_account_id, platform, status) VALUES (%s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), str(company_id), "ext123", "facebook", "active")
    )
    print("Insert succeeded!")
    conn.commit()
    print("Commit succeeded!")
except Exception as e:
    print(f"Failed: {e}")
