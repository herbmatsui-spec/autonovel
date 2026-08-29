"""Add story_canvas tables (story_nodes, story_edges)

Revision ID: 115dcdfc0063
Revises: 20260828150000
Create Date: 2026-08-29 00:17:16.922795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '115dcdfc0063'
down_revision: Union[str, Sequence[str], None] = '20260828150000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'story_nodes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('label', sa.String(500), nullable=False),
        sa.Column('ep_num', sa.Integer(), nullable=True),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True),
        sa.Column('x', sa.Float(), default=0.0),
        sa.Column('y', sa.Float(), default=0.0),
        sa.Column('data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_story_nodes_book_id', 'story_nodes', ['book_id'])
    op.create_index('idx_story_nodes_kind', 'story_nodes', ['kind'])

    op.create_table(
        'story_edges',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('target', sa.String(100), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_story_edges_book_id', 'story_edges', ['book_id'])
    op.create_index('idx_story_edges_source', 'story_edges', ['source'])
    op.create_index('idx_story_edges_target', 'story_edges', ['target'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_story_edges_target', table_name='story_edges')
    op.drop_index('idx_story_edges_source', table_name='story_edges')
    op.drop_index('idx_story_edges_book_id', table_name='story_edges')
    op.drop_table('story_edges')

    op.drop_index('idx_story_nodes_kind', table_name='story_nodes')
    op.drop_index('idx_story_nodes_book_id', table_name='story_nodes')
    op.drop_table('story_nodes')