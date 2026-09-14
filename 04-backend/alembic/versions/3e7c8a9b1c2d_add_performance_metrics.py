"""add_performance_metrics_to_campaign_run_stat

Revision ID: 3e7c8a9b1c2d
Revises: 286b997e3b1b
Create Date: 2026-09-14 18:55:20.620494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e7c8a9b1c2d'
down_revision: Union[str, Sequence[str], None] = '286b997e3b1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('campaign_run_stats', sa.Column('clicks', sa.Integer(), server_default='0', nullable=False))
    op.add_column('campaign_run_stats', sa.Column('impressions', sa.Integer(), server_default='0', nullable=False))
    op.add_column('campaign_run_stats', sa.Column('conversions', sa.Numeric(precision=20, scale=4), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('campaign_run_stats', 'conversions')
    op.drop_column('campaign_run_stats', 'impressions')
    op.drop_column('campaign_run_stats', 'clicks')
