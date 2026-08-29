"""add axis_lock_flags column to books

Revision ID: 20260828150000
Revises: 20260826140000
Create Date: 2026-08-28 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260828150000'
down_revision = '20260826140000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add column axis_lock_flags to books
    op.add_column('books', sa.Column('axis_lock_flags', sa.Text(), nullable=False, server_default='{}'))


def downgrade() -> None:
    op.drop_column('books', 'axis_lock_flags')