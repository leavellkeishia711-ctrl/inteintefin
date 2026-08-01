"""enforce rls on remaining tables

Revision ID: e8acf4873fc7
Revises: 0002_rls
Create Date: 2026-07-31 09:48:20.312061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8acf4873fc7'
down_revision: Union[str, Sequence[str], None] = '0002_rls'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    tables_with_company_id = [
        "campaign_run_stats",
        "decision_recommendations",
        "invites",
        "payroll_line_items",
        "telegram_link_tokens"
    ]
    for table in tables_with_company_id:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} FOR ALL TO app_user USING (company_id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (company_id = nullif(current_setting('app.company_id', true), '')::uuid);")

    # companies uses id instead of company_id
    op.execute("ALTER TABLE companies ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE companies FORCE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY tenant_isolation ON companies FOR ALL TO app_user USING (id = nullif(current_setting('app.company_id', true), '')::uuid) WITH CHECK (id = nullif(current_setting('app.company_id', true), '')::uuid);")

    # fx_rates is global, anyone can read
    op.execute("ALTER TABLE fx_rates ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE fx_rates FORCE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY tenant_isolation ON fx_rates FOR ALL TO app_user USING (true) WITH CHECK (false);")

    # Grant privileges to app_user
    op.execute("GRANT USAGE ON SCHEMA public TO app_user;")
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;")


def downgrade() -> None:
    """Downgrade schema."""
    pass
