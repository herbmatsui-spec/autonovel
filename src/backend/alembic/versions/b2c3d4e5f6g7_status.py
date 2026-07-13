"""add_status_to_books

Revision ID: b2c3d4e5f6g7_status
Revises: a1b2c3d4e5f6_catchcopy
Create Date: 2026-07-13 13:17:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7_status'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6_catchcopy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(50), nullable=True, server_default='draft'))


def downgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_column('status')
