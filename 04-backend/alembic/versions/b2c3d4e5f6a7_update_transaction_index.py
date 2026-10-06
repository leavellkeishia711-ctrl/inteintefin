"""update_transaction_index

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-06 12:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Drop old index and recreate with new predicate
    op.drop_index('uix_company_source_external', table_name='transactions')
    op.create_index(
        'uix_company_source_external', 
        'transactions', 
        ['company_id', 'source', 'external_id'], 
        unique=True, 
        postgresql_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL")
    )

def downgrade() -> None:
    op.drop_index('uix_company_source_external', table_name='transactions')
    op.create_index(
        'uix_company_source_external', 
        'transactions', 
        ['company_id', 'source', 'external_id'], 
        unique=True, 
        postgresql_where=sa.text("external_id IS NOT NULL")
    )
