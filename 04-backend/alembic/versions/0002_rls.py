"""rls

Revision ID: 0002_rls
Revises: 
Create Date: 2026-07-31 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_rls'
down_revision = 'c823966262b9'
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "users", "teams", "transactions", "ad_accounts", "campaigns",
    "campaign_runs", "consumables", "affiliate_networks", "partner_payouts",
    "alerts", "audit_log", "compensation_plans", "payroll_runs", "chat_messages",
    "import_batches", "import_rows"
]

def upgrade() -> None:
    for table in TENANT_TABLES:
        # Enable and force RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        
        # Create policy
        policy_sql = f"""
        CREATE POLICY tenant_isolation ON {table} FOR ALL TO app_user
        USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid)
        WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);
        """
        op.execute(policy_sql)


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
