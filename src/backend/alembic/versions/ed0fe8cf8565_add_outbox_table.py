"""add outbox table

Revision ID: ed0fe8cf8565
Revises: 87c95cf1594c
Create Date: 2026-06-07 14:04:20.905545

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ed0fe8cf8565'
down_revision: Union[str, Sequence[str], None] = '87c95cf1594c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'outbox',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('ix_outbox_status', 'outbox', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_outbox_status', table_name='outbox')
    op.drop_table('outbox')

