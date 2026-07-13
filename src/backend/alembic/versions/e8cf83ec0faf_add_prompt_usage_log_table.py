"""add prompt_usage_log table

Revision ID: e8cf83ec0faf
Revises: f3a1b2c4d5e6
Create Date: 2026-07-08 08:44:35.720282

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e8cf83ec0faf'
down_revision: Union[str, Sequence[str], None] = 'f3a1b2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('prompt_usage_log',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('template_name', sa.String(length=255), nullable=False),
        sa.Column('hits', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_time_ms', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('avg_time_ms', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_prompt_usage_timestamp', 'prompt_usage_log', ['timestamp'])
    op.create_index('idx_prompt_usage_template', 'prompt_usage_log', ['template_name'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('prompt_usage_log')
