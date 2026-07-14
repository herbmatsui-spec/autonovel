"""add catchcopy to books

Revision ID: 0002_add_catchcopy
Revises: 0001_erotic_intensity
"""
import sqlalchemy as sa

from alembic import op

revision = '0002_add_catchcopy'
down_revision = '0001_erotic_intensity'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.add_column(sa.Column('catchcopy', sa.String(255), nullable=True, server_default=''))

def downgrade() -> None:
    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_column('catchcopy')
