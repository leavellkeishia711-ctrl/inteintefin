"""add_campaign_run_reconciliation

Revision ID: 417a8e52a781
Revises: 3e7c8a9b1c2d
Create Date: 2026-09-14 20:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '417a8e52a781'
down_revision: Union[str, Sequence[str], None] = '3e7c8a9b1c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'campaign_run_reconciliations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('campaign_run_id', sa.Uuid(), nullable=False),
        sa.Column('stat_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('chosen_source', sa.String(), nullable=True),
        sa.Column('chosen_stat_id', sa.Uuid(), nullable=True),
        sa.Column('canonical_spend', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('canonical_revenue', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('canonical_clicks', sa.Integer(), nullable=True),
        sa.Column('canonical_impressions', sa.Integer(), nullable=True),
        sa.Column('canonical_conversions', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('canonical_currency', sa.CHAR(length=3), nullable=True),
        sa.Column('observed_source_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('conflict_fields', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('source_snapshot', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('decision_reason', sa.String(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('reconciled', 'partial', 'conflict', 'no_data')", name='check_reconciliation_status'),
        sa.ForeignKeyConstraint(['campaign_run_id'], ['campaign_runs.id'], ),
        sa.ForeignKeyConstraint(['chosen_stat_id'], ['campaign_run_stats.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reconciliation_company_date', 'campaign_run_reconciliations', ['company_id', 'stat_date'], unique=False)
    op.create_index('ix_reconciliation_company_status_date', 'campaign_run_reconciliations', ['company_id', 'status', 'stat_date'], unique=False)
    op.create_index(
        'uq_campaign_run_reconciliations_active', 
        'campaign_run_reconciliations', 
        ['company_id', 'campaign_run_id', 'stat_date'], 
        unique=True, 
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # RLS Enablement
    op.execute("ALTER TABLE campaign_run_reconciliations ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY select_reconciliations ON campaign_run_reconciliations "
        "FOR SELECT USING (company_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::uuid);"
    )
    op.execute(
        "CREATE POLICY insert_reconciliations ON campaign_run_reconciliations "
        "FOR INSERT WITH CHECK (company_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::uuid);"
    )
    op.execute(
        "CREATE POLICY update_reconciliations ON campaign_run_reconciliations "
        "FOR UPDATE USING (company_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::uuid) "
        "WITH CHECK (company_id = NULLIF(current_setting('app.current_tenant', TRUE), '')::uuid);"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON campaign_run_reconciliations TO app_user;")

def downgrade() -> None:
    op.execute("DROP POLICY update_reconciliations ON campaign_run_reconciliations;")
    op.execute("DROP POLICY insert_reconciliations ON campaign_run_reconciliations;")
    op.execute("DROP POLICY select_reconciliations ON campaign_run_reconciliations;")
    op.drop_index('uq_campaign_run_reconciliations_active', table_name='campaign_run_reconciliations', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_reconciliation_company_status_date', table_name='campaign_run_reconciliations')
    op.drop_index('ix_reconciliation_company_date', table_name='campaign_run_reconciliations')
    op.drop_table('campaign_run_reconciliations')
