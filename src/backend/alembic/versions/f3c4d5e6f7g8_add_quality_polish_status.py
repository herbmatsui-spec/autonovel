"""add_quality_polish_status_to_plot

Revision ID: f3c4d5e6f7g8_add_quality_polish_status
Revises: f2b3c4d5e6f7_add_sharp_edges_json
Create Date: 2026-07-09 00:02:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'f3c4d5e6f7g8_add_quality_polish_status'
down_revision: Union[str, Sequence[str], None] = 'f2b3c4d5e6f7_add_sharp_edges_json'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('plot', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quality_polish_status', sa.String(), nullable=True, server_default='pending'))


def downgrade() -> None:
    with op.batch_alter_table('plot', schema=None) as batch_op:
        batch_op.drop_column('quality_polish_status')
