"""add_simulation_fields_to_plot

Revision ID: f3a1b2c4d5e6
Revises: c2d671bd984b
Create Date: 2026-06-24 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3a1b2c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c2d671bd984b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add is_simulation, simulation_id, pov_character_id to plot.
    Also update primary key to include simulation_id (requires batch mode for SQLite).
    """
    # Add pov_character_id if it doesn't exist yet
    try:
        op.add_column('plot', sa.Column('pov_character_id', sa.Integer(), nullable=True))
    except Exception:
        pass  # Column may already exist

    # Use batch_alter_table to recreate the table with the new PK and new columns
    # SQLite does not support ALTER TABLE ADD COLUMN to primary key directly,
    # so we must use batch mode which recreates the table.
    with op.batch_alter_table(
        'plot',
        table_kwargs={'sqlite_autoincrement': False},
    ) as batch_op:
        # Add new columns
        try:
            batch_op.add_column(sa.Column('is_simulation', sa.Boolean(), server_default=sa.text('0'), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('simulation_id', sa.String(), server_default='', nullable=True))
        except Exception:
            pass

        # Update the primary key to include simulation_id
        # Drop old PK and create new one
        batch_op.create_primary_key('pk_plot', ['branch_id', 'ep_num', 'simulation_id'])


def downgrade() -> None:
    """Downgrade schema: remove is_simulation, simulation_id; restore old PK."""
    with op.batch_alter_table('plot') as batch_op:
        batch_op.create_primary_key('pk_plot', ['branch_id', 'ep_num'])
        batch_op.drop_column('simulation_id')
        batch_op.drop_column('is_simulation')

    try:
        op.drop_column('plot', 'pov_character_id')
    except Exception:
        pass

