import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=True)
    conn.execute("""
    CREATE OR REPLACE FUNCTION set_app_company_id(cid text) 
    RETURNS void AS $$ 
    BEGIN 
        PERFORM set_config('app.company_id', cid, true); 
    END; 
    $$ LANGUAGE plpgsql;
    """)
    print("Function created!")
except Exception as e:
    print(f"Failed: {e}")
