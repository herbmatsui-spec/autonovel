"""add_sharp_edges_json_to_plot

Revision ID: f2b3c4d5e6f7_add_sharp_edges_json
Revises: f1a2b3c4d5e6_add_emotional_hook_json
Create Date: 2026-07-09 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'f2b3c4d5e6f7_add_sharp_edges_json'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6_add_emotional_hook_json'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('plot', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sharp_edges_json', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('plot', schema=None) as batch_op:
        batch_op.drop_column('sharp_edges_json')
