"""add name to ad_accounts

Revision ID: 5f9e8a7c6d5b
Revises: b7d23a9b1c1e
Create Date: 2026-09-04 15:43:35.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5f9e8a7c6d5b'
down_revision: Union[str, None] = 'b7d23a9b1c1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('ad_accounts', sa.Column('name', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('ad_accounts', 'name')
