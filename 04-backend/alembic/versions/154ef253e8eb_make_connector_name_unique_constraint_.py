"""make connector name unique constraint partial

Revision ID: 154ef253e8eb
Revises: 2a5ebeceefb0
Create Date: 2026-09-13 21:58:56.749213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '154ef253e8eb'
down_revision: Union[str, Sequence[str], None] = '2a5ebeceefb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("uix_company_connector", "connector_configs", type_="unique")
    op.create_index("uix_company_connector", "connector_configs", ["company_id", "connector_name"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uix_company_connector", table_name="connector_configs")
    op.create_unique_constraint("uix_company_connector", "connector_configs", ["company_id", "connector_name"])
