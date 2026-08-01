import os
import psycopg2
from dotenv import load_dotenv
import time

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql').replace(':5432', ':6543').replace('?sslmode=require', '').replace('&sslmode=require', '')
tables = ['campaign_run_stats', 'decision_recommendations', 'invites', 'payroll_line_items', 'telegram_link_tokens']

for t in tables:
    conn = psycopg2.connect(url, sslmode='require')
    conn.autocommit = True
    cursor = conn.cursor()
    print(f"Applying to {t}...")
    try:
        cursor.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")
        cursor.execute(f"CREATE POLICY tenant_isolation ON {t} USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);")
    except Exception as e:
        print(f"Error on {t}: {e}")
    conn.close()
    time.sleep(1)

# companies
conn = psycopg2.connect(url, sslmode='require')
conn.autocommit = True
cursor = conn.cursor()
print(f"Applying to companies...")
try:
    cursor.execute("ALTER TABLE companies FORCE ROW LEVEL SECURITY;")
    cursor.execute("CREATE POLICY tenant_isolation ON companies USING (id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (id = nullif(current_setting('app.company_id', true), '')::uuid);")
except Exception as e:
    print(f"Error on companies: {e}")
conn.close()

# fx_rates
conn = psycopg2.connect(url, sslmode='require')
conn.autocommit = True
cursor = conn.cursor()
print(f"Applying to fx_rates...")
try:
    cursor.execute("ALTER TABLE fx_rates FORCE ROW LEVEL SECURITY;")
    cursor.execute("CREATE POLICY tenant_isolation ON fx_rates USING (true) WITH CHECK (false);")
except Exception as e:
    print(f"Error on fx_rates: {e}")
conn.close()

print("Done!")
