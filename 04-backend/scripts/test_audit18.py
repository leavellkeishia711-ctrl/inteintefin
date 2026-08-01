import os
import psycopg
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=False)
    cur = conn.cursor()
    
    print("Inserting into ad_accounts with bad company_id...")
    cur.execute(
        "INSERT INTO ad_accounts (id, company_id, external_account_id, platform, status) VALUES (%s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), str(uuid.uuid4()), "ext123", "facebook", "active")
    )
    print("Insert succeeded!")
    conn.commit()
    print("Commit succeeded!")
except Exception as e:
    print(f"Failed: {e}")
