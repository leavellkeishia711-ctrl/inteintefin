import os
import psycopg
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=False, prepare_threshold=None)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM companies LIMIT 1")
    company_id = cur.fetchone()[0]
    
    cur.execute("SELECT id FROM users LIMIT 1")
    user_id = cur.fetchone()[0]

    print(f"Testing insert for company {company_id}, user {user_id}")
    
    cur.execute("SELECT set_config('app.company_id', %s, true)", (str(company_id),))

    print("Inserting...")
    cur.execute(
        "INSERT INTO audit_log (id, company_id, actor_user_id, entity_type, action) VALUES (%s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), str(company_id), str(user_id), "transaction", "create")
    )
    print("Insert succeeded!")
    conn.commit()
    print("Commit succeeded!")
except Exception as e:
    print(f"Failed: {e}")
