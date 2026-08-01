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
    
    jwt_claims = json.dumps({"app_metadata": {"company_id": str(uuid.uuid4())}})
    cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (jwt_claims,))
    
    print("Inserting into dummy2...")
    cur.execute("INSERT INTO dummy2 (id) VALUES (%s)", (str(uuid.uuid4()),))
    print("Insert succeeded!")
    
    conn.commit()
    print("Commit succeeded!")
except Exception as e:
    print(f"Failed: {e}")
