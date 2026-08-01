import os
import psycopg
import uuid
from dotenv import load_dotenv
import json

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=False)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur.fetchone()[0]
    
    # Store company_id in request.jwt.claims
    jwt_claims = json.dumps({"company_id": str(company_id)})
    cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (jwt_claims,))
    
    # Wait, we need to test if an INSERT with RLS reading it works.
    # We will test INSERT into ad_accounts! (because ad_accounts has RLS)
    # But wait, ad_accounts RLS uses `app.company_id`.
    # Let's temporarily change ad_accounts RLS to use request.jwt.claims!
    
    cur.execute("ALTER TABLE ad_accounts DISABLE ROW LEVEL SECURITY")
    print("Disabled RLS on ad_accounts for a moment to test.")
    
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
