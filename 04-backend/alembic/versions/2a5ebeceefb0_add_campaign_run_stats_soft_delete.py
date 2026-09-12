"""add_campaign_run_stats_soft_delete

Revision ID: 2a5ebeceefb0
Revises: 5f9e8a7c6d5b
Create Date: 2026-09-12 13:08:48.367761

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a5ebeceefb0'
down_revision: Union[str, Sequence[str], None] = '5f9e8a7c6d5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add deleted_at column
    op.add_column('campaign_run_stats', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # 2. Check for duplicates for external_id IS NULL
    conn = op.get_bind()
    res = conn.execute(sa.text("""
        SELECT company_id, campaign_run_id, stat_date, source
        FROM campaign_run_stats
        WHERE external_id IS NULL
        GROUP BY company_id, campaign_run_id, stat_date, source
        HAVING COUNT(*) > 1
    """)).fetchall()
    
    if res:
        raise ValueError(
            f"Found existing duplicates in campaign_run_stats with external_id IS NULL. "
            f"Cannot create unique index uq_campaign_run_stats_null_ext. "
            f"Please resolve manually. Duplicates: {res}"
        )
        
    # 3. Drop existing index
    op.drop_index('uq_campaign_run_stats', table_name='campaign_run_stats')
    
    # 4. Create new index replacing the old one
    op.create_index(
        'uq_campaign_run_stats', 
        'campaign_run_stats', 
        ['company_id', 'campaign_run_id', 'stat_date', 'source', 'external_id'],
        unique=True,
        postgresql_where=sa.text('external_id IS NOT NULL AND deleted_at IS NULL'),
        sqlite_where=sa.text('external_id IS NOT NULL AND deleted_at IS NULL')
    )
    
    # 5. Create the new null external_id index
    op.create_index(
        'uq_campaign_run_stats_null_ext',
        'campaign_run_stats',
        ['company_id', 'campaign_run_id', 'stat_date', 'source'],
        unique=True,
        postgresql_where=sa.text('external_id IS NULL AND deleted_at IS NULL'),
        sqlite_where=sa.text('external_id IS NULL AND deleted_at IS NULL')
    )


def downgrade() -> None:
    # 1. Drop new index
    op.drop_index('uq_campaign_run_stats_null_ext', table_name='campaign_run_stats')
    
    # 2. Revert modified index
    op.drop_index('uq_campaign_run_stats', table_name='campaign_run_stats')
    op.create_index(
        'uq_campaign_run_stats',
        'campaign_run_stats',
        ['company_id', 'campaign_run_id', 'stat_date', 'source', 'external_id'],
        unique=True,
        postgresql_where=sa.text('external_id IS NOT NULL'),
        sqlite_where=sa.text('external_id IS NOT NULL')
    )
    
    # 3. Drop column
    op.drop_column('campaign_run_stats', 'deleted_at')
