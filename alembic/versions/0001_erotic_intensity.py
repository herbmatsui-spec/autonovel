"""add erotic_intensity to plot

Revision ID: 0001_erotic_intensity
Revises: 00000000_initial_migration
"""
import sqlalchemy as sa

from alembic import op

revision = '0001_erotic_intensity'
down_revision = '00000000_initial_migration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # SQLite互換: batch modeを使用
    with op.batch_alter_table('plots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('erotic_intensity', sa.Integer(), nullable=True, server_default='0'))

def downgrade() -> None:
    with op.batch_alter_table('plots', schema=None) as batch_op:
        batch_op.drop_column('erotic_intensity')
