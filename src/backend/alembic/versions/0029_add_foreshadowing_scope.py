"""create foreshadowings and character_relations tables

Revision ID: 0029_foreshadowing_relations
Revises: 0028_billing_and_credits
Create Date: 2026-09-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0029_foreshadowing_relations'
down_revision = '0028_billing_and_credits'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 伏線ステートマシンテーブル
    op.create_table(
        'foreshadowings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('planted_episode', sa.Integer(), nullable=False),
        sa.Column('target_episode', sa.Integer(), nullable=True),
        sa.Column('resolved_episode', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(length=32), nullable=False, server_default='short_term'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='planted'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_foreshadowings_book_id', 'foreshadowings', ['book_id'])
    op.create_index('ix_foreshadowings_status', 'foreshadowings', ['status'])
    # 複合インデックス: 特定作品の未回収伏線を高速取得
    op.create_index(
        'ix_foreshadowings_book_status',
        'foreshadowings',
        ['book_id', 'status'],
    )

    # キャラクター関係テーブル（グラフDB Edgeのリレーショナル置換）
    op.create_table(
        'character_relations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('source_char_id', sa.Integer(), nullable=False),
        sa.Column('target_char_id', sa.Integer(), nullable=False),
        sa.Column('relation_type', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_character_relations_book_id', 'character_relations', ['book_id'])


def downgrade() -> None:
    op.drop_table('character_relations')
    op.drop_table('foreshadowings')