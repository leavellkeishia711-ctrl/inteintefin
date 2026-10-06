"""add_import_row_model

Revision ID: d71cca8e84be
Revises: 7770fa13b699
Create Date: 2026-10-06 14:08:10.827465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd71cca8e84be'
down_revision: Union[str, Sequence[str], None] = '7770fa13b699'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'import_rows',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('batch_id', sa.Uuid(), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('row_data', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batches.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'valid', 'imported', 'error')", name='check_import_row_status')
    )
    op.create_index('ix_import_rows_batch_id', 'import_rows', ['batch_id'], unique=False)
    # Ensure RLS is active on the table (since it's CompanyScoped)
    op.execute("ALTER TABLE import_rows ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE import_rows FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation_policy ON import_rows USING (company_id = current_setting('app.current_tenant', true)::uuid)")

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_import_rows_batch_id', table_name='import_rows')
    op.drop_table('import_rows')
