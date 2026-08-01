import os
import psycopg
import uuid
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=False)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur.fetchone()[0]
    
    jwt_claims = json.dumps({"company_id": str(company_id)})
    cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (jwt_claims,))
    
    # We will NOT alter table here. We will just insert into ad_accounts.
    # Note: RLS is still enabled on ad_accounts, and it checks app.company_id.
    # Since we didn't set app.company_id, it will be NULL.
    # The insert into ad_accounts should THROW an error (because it violates RLS with check, or FK).
    
    print("Inserting into ad_accounts...")
    cur.execute(
        "INSERT INTO ad_accounts (id, company_id, external_account_id, platform, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), str(company_id), "ext123", "facebook", "active", datetime.now(), datetime.now())
    )
    print("Insert succeeded!")
    conn.commit()
    print("Commit succeeded!")
except Exception as e:
    print(f"Failed: {e}")
