"""add scope column to foreshadowings table

Revision ID: 0030_add_foreshadowing_scope
Revises: 0029_foreshadowing_relations
Create Date: 2026-09-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0030_add_foreshadowing_scope'
down_revision = '0029_foreshadowing_relations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 伏線テーブルにscopeカラムを追加
    op.add_column('foreshadowings', sa.Column('scope', sa.String(length=32), nullable=False, server_default='short_term'))


def downgrade() -> None:
    op.drop_column('foreshadowings', 'scope')