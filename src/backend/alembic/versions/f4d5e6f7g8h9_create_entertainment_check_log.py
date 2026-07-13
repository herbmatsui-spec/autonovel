"""create entertainment_check_log table

Revision ID: f4d5e6f7g8h9_create_entertainment_check_log
Revises: f3c4d5e6f7g8_add_quality_polish_status
Create Date: 2026-07-09 00:03:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'f4d5e6f7g8h9_create_entertainment_check_log'
down_revision: Union[str, Sequence[str], None] = 'f3c4d5e6f7g8_add_quality_polish_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entertainment_check_log',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('ep_num', sa.Integer(), nullable=False),
        sa.Column('interest_score', sa.Integer(), nullable=True),
        sa.Column('physiological_reaction', sa.String(length=255), nullable=True),
        sa.Column('would_continue_reading', sa.Boolean(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_entertainment_check_log_book_ep', 'entertainment_check_log', ['book_id', 'ep_num'])


def downgrade() -> None:
    op.drop_index('idx_entertainment_check_log_book_ep', table_name='entertainment_check_log')
    op.drop_table('entertainment_check_log')
