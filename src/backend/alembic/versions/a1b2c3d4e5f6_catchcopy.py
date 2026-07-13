"""add_catchcopy_to_books

Revision ID: a1b2c3d4e5f6_catchcopy
Revises: f3a1b2c4d5e6
Create Date: 2026-07-13 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6_catchcopy'
down_revision: Union[str, Sequence[str], None] = 'f3a1b2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.add_column(sa.Column('catchcopy', sa.String(255), nullable=True, server_default=''))
        batch_op.add_column(sa.Column('status', sa.String(50), nullable=True, server_default='draft'))


def downgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('catchcopy')
