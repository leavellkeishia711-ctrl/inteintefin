import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

try:
    conn = psycopg.connect(url, autocommit=True)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE IF NOT EXISTS dummy (id serial primary key, val text)")
    print("Created table")
    
    cur.execute("INSERT INTO dummy (val) VALUES ('test')")
    print("Inserted")
    
    cur.execute("SELECT * FROM dummy")
    print(cur.fetchall())
except Exception as e:
    print(f"Failed: {e}")
