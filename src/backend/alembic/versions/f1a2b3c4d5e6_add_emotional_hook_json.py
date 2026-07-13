"""add_emotional_hook_json_to_plot

Revision ID: f1a2b3c4d5e6_add_emotional_hook_json
Revises: e8cf83ec0faf
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'f1a2b3c4d5e6_add_emotional_hook_json'
down_revision: Union[str, Sequence[str], None] = 'e8cf83ec0faf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('plot', schema=None) as batch_op:
        batch_op.add_column(sa.Column('emotional_hook_json', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('plot', schema=None) as batch_op:
        batch_op.drop_column('emotional_hook_json')
