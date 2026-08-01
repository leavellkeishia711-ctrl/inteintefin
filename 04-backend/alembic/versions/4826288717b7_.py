"""drop audit_log bogus fks on entity_id and request_id

entity_id and request_id are polymorphic UUID fields that were
incorrectly constrained with FK to companies.id in the initial
migration.

Revision ID: 4826288717b7
Revises: e8acf4873fc7
Create Date: 2026-07-31 16:45:59.493375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4826288717b7'
down_revision: Union[str, Sequence[str], None] = 'e8acf4873fc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('audit_log_entity_id_fkey', 'audit_log', type_='foreignkey')
    op.drop_constraint('audit_log_request_id_fkey', 'audit_log', type_='foreignkey')


def downgrade() -> None:
    op.create_foreign_key('audit_log_entity_id_fkey', 'audit_log', 'companies', ['entity_id'], ['id'])
    op.create_foreign_key('audit_log_request_id_fkey', 'audit_log', 'companies', ['request_id'], ['id'])
