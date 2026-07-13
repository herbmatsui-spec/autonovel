"""add_emotional_resonance_fields_to_plot

Revision ID: e5c60770afa0
Revises: ad2d7c58ee0f
Create Date: 2026-06-06 11:48:02.823451

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5c60770afa0'
down_revision: Union[str, Sequence[str], None] = 'ad2d7c58ee0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('plot', sa.Column('emotional_resonance_score', sa.Integer(), server_default='0', nullable=True))
    op.add_column('plot', sa.Column('thematic_depth_score', sa.Integer(), server_default='0', nullable=True))
    op.add_column('plot', sa.Column('literary_beauty_score', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('plot') as batch_op:
        batch_op.drop_column('literary_beauty_score')
        batch_op.drop_column('thematic_depth_score')
        batch_op.drop_column('emotional_resonance_score')

