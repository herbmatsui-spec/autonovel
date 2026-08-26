"""Merge multiple heads

Revision ID: 19641492fe26
Revises: c3d4e5f6g7h8_plot_columns, f4d5e6f7g8h9_create_entertainment_check_log
Create Date: 2026-08-26 17:01:19.751496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19641492fe26'
down_revision: Union[str, Sequence[str], None] = ('c3d4e5f6g7h8_plot_columns', 'f4d5e6f7g8h9_create_entertainment_check_log')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
