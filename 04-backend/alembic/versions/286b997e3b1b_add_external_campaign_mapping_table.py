"""add_external_campaign_mapping_table

Revision ID: 286b997e3b1b
Revises: 154ef253e8eb
Create Date: 2026-09-14 10:28:59.363417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '286b997e3b1b'
down_revision: Union[str, Sequence[str], None] = '154ef253e8eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'external_campaign_mappings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('campaign_run_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['campaign_run_id'], ['campaign_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'uix_company_platform_external_campaign', 
        'external_campaign_mappings', 
        ['company_id', 'platform', 'external_id'], 
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL')
    )
    
    op.execute("ALTER TABLE external_campaign_mappings ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_external_campaign_mappings
        ON external_campaign_mappings
        FOR ALL
        USING (company_id = current_setting('app.current_company_id')::uuid)
        WITH CHECK (company_id = current_setting('app.current_company_id')::uuid);
    """)



def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_external_campaign_mappings ON external_campaign_mappings;")
    op.drop_index('uix_company_platform_external_campaign', table_name='external_campaign_mappings')
    op.drop_table('external_campaign_mappings')

