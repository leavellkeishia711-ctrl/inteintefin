import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql').replace(':5432', ':6543').replace('?sslmode=require', '').replace('&sslmode=require', '')
conn = psycopg2.connect(url, sslmode='require')
conn.autocommit = True
cursor = conn.cursor()
tables = ['campaign_run_stats', 'decision_recommendations', 'invites', 'payroll_line_items', 'telegram_link_tokens']
for t in tables:
    cursor.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
    cursor.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")
    cursor.execute(f"CREATE POLICY tenant_isolation ON {t} USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);")

cursor.execute("ALTER TABLE companies ENABLE ROW LEVEL SECURITY;")
cursor.execute("ALTER TABLE companies FORCE ROW LEVEL SECURITY;")
cursor.execute("CREATE POLICY tenant_isolation ON companies USING (id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (id = nullif(current_setting('app.company_id', true), '')::uuid);")

cursor.execute("ALTER TABLE fx_rates ENABLE ROW LEVEL SECURITY;")
cursor.execute("ALTER TABLE fx_rates FORCE ROW LEVEL SECURITY;")
cursor.execute("CREATE POLICY tenant_isolation ON fx_rates USING (true) WITH CHECK (false);")

# Also record that the migration was run
try:
    cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('e8acf4873fc7');")
except Exception:
    cursor.execute("UPDATE alembic_version SET version_num = 'e8acf4873fc7';")

print("Migrations applied!")
