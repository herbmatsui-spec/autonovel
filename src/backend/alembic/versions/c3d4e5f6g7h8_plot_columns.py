"""add_missing_plot_columns

Revision ID: c3d4e5f6g7h8_plot_columns
Revises: b2c3d4e5f6g7_status
Create Date: 2026-07-13 13:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8_plot_columns'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('plots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target_tension', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('is_simulation', sa.Boolean(), server_default=sa.text('0'), nullable=True))
        batch_op.add_column(sa.Column('simulation_id', sa.String(), server_default='', nullable=True))
        batch_op.add_column(sa.Column('pov_character_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('plots', schema=None) as batch_op:
        batch_op.drop_column('pov_character_id')
        batch_op.drop_column('simulation_id')
        batch_op.drop_column('is_simulation')
        batch_op.drop_column('target_tension')
