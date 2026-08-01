import os
import psycopg
import uuid
from dotenv import load_dotenv
import json

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn1 = psycopg.connect(url, autocommit=True)
    cur1 = conn1.cursor()
    cur1.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur1.fetchone()[0]
    conn1.close()
    
    jwt_claims = json.dumps({"company_id": str(company_id)})
    conn = psycopg.connect(url, options=f"-c request.jwt.claims='{jwt_claims}'", autocommit=False)
    cur = conn.cursor()
    
    print("Checking request.jwt.claims...")
    cur.execute("SHOW request.jwt.claims")
    print(f"request.jwt.claims = {cur.fetchone()[0]}")
except Exception as e:
    print(f"Failed: {e}")
