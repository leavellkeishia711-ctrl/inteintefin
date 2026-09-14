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
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
