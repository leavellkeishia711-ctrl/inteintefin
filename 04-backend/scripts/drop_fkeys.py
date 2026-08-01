import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(url, autocommit=True)

try:
    conn.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_company_id_fkey")
    print("Dropped company_id fkey")
except Exception as e:
    print(f"Error dropping company_id fkey: {e}")

try:
    conn.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_actor_user_id_fkey")
    print("Dropped actor_user_id fkey")
except Exception as e:
    print(f"Error dropping actor_user_id fkey: {e}")

try:
    conn.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_entity_id_fkey")
    print("Dropped entity_id fkey")
except Exception as e:
    print(f"Error dropping entity_id fkey: {e}")

try:
    conn.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_request_id_fkey")
    print("Dropped request_id fkey")
except Exception as e:
    print(f"Error dropping request_id fkey: {e}")
