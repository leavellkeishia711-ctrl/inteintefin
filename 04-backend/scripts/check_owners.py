import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql').replace(':5432', ':6543').replace('?sslmode=require', '').replace('&sslmode=require', '')
conn = psycopg2.connect(url, sslmode='require')
cursor = conn.cursor()
cursor.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public';")
print(cursor.fetchall())
