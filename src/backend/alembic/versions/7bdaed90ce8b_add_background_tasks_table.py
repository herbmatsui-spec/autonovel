"""add background tasks table

Revision ID: 7bdaed90ce8b
Revises: ed0fe8cf8565
Create Date: 2026-06-07 14:23:21.847264

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7bdaed90ce8b'
down_revision: Union[str, Sequence[str], None] = 'ed0fe8cf8565'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'background_tasks',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('sub_message', sa.Text(), nullable=True),
        sa.Column('streaming_text', sa.Text(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('result_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )


def downgrade() -> None:
    op.drop_table('background_tasks')

