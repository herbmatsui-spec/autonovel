"""rename_stress_to_tension_delta

Revision ID: 87c95cf1594c
Revises: e5c60770afa0
Create Date: 2026-06-06 14:03:35.798088

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '87c95cf1594c'
down_revision: Union[str, Sequence[str], None] = 'e5c60770afa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('books', 'cumulative_stress', new_column_name='cumulative_tension')
    op.alter_column('chapters', 'stress_delta', new_column_name='tension_delta')
    op.alter_column('plot', 'stress', new_column_name='tension_delta')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('books', 'cumulative_tension', new_column_name='cumulative_stress')
    op.alter_column('chapters', 'tension_delta', new_column_name='stress_delta')
    op.alter_column('plot', 'tension_delta', new_column_name='stress')



