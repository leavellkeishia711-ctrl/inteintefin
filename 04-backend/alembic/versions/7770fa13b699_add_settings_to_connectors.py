"""add settings to connectors

Revision ID: 7770fa13b699
Revises: 417a8e52a781
Create Date: 2026-10-05 11:52:25.680556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7770fa13b699'
down_revision: Union[str, Sequence[str], None] = '417a8e52a781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('connector_configs', sa.Column('settings', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('connector_configs', 'settings')
