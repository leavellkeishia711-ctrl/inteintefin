import os
import psycopg
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=True)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur.fetchone()[0]
    
    cur.execute("SELECT id FROM users LIMIT 1")
    user_id = cur.fetchone()[0]

    print("Inserting into audit_log without set_config...")
    cur.execute(
        "INSERT INTO audit_log (id, company_id, actor_user_id, entity_type, action) VALUES (%s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), str(company_id), str(user_id), "transaction", "create")
    )
    print("Insert succeeded!")
except Exception as e:
    print(f"Failed: {e}")
