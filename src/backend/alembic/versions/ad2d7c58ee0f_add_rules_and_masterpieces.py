"""Add rules and masterpieces tables

Revision ID: ad2d7c58ee0f
Revises: 262b595ebb00
Create Date: 2026-06-05 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ad2d7c58ee0f'
down_revision: Union[str, Sequence[str], None] = '262b595ebb00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('target_word', sa.String(), nullable=False),
        sa.Column('instruction', sa.Text(), nullable=False),
        sa.Column('level', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('character_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('updated_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'masterpieces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('emotion_or_scene', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('vector_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('masterpieces')
    op.drop_table('rules')

