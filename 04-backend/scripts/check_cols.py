import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql').replace(':5432', ':6543').replace('?sslmode=require', '').replace('&sslmode=require', '')
conn = psycopg2.connect(url, sslmode='require')
cursor = conn.cursor()
cursor.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_name IN ('campaign_run_stats', 'companies', 'decision_recommendations', 'fx_rates', 'invites', 'payroll_line_items', 'telegram_link_tokens') AND column_name IN ('company_id', 'id');")
print(cursor.fetchall())
