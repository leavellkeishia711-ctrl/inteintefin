import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql').replace(':5432', ':6543').replace('?sslmode=require', '').replace('&sslmode=require', '')
conn = psycopg2.connect(url, sslmode='require')
cursor = conn.cursor()
sql = """
ALTER TABLE invites FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invites USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);

ALTER TABLE payroll_line_items FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON payroll_line_items USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);

ALTER TABLE telegram_link_tokens FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON telegram_link_tokens USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);

ALTER TABLE companies FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON companies USING (id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (id = nullif(current_setting('app.company_id', true), '')::uuid);

ALTER TABLE fx_rates FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON fx_rates USING (true) WITH CHECK (false);
"""
cursor.execute(sql)
conn.commit()
print("Remaining policies applied!")
