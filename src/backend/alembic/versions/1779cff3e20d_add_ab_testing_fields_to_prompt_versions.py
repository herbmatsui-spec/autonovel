"""add_ab_testing_fields_to_prompt_versions

Revision ID: 1779cff3e20d
Revises: c916c38a8e17
Create Date: 2026-06-16 13:31:02.458995

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1779cff3e20d'
down_revision: Union[str, Sequence[str], None] = 'c916c38a8e17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    try:
        op.add_column('prompt_versions', sa.Column('score_before', sa.Float(), nullable=True))
    except Exception as e:
        print(f"Skipping add_column score_before: {e}")
    try:
        op.add_column('prompt_versions', sa.Column('score_after', sa.Float(), nullable=True))
    except Exception as e:
        print(f"Skipping add_column score_after: {e}")
    try:
        op.add_column('prompt_versions', sa.Column('rollback_reason', sa.String(), nullable=True))
    except Exception as e:
        print(f"Skipping add_column rollback_reason: {e}")
    try:
        with op.batch_alter_table('prompt_versions') as batch_op:
            batch_op.add_column(sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id', ondelete='CASCADE', name='fk_prompt_versions_book_id'), nullable=True))
    except Exception as e:
        print(f"Skipping batch add_column book_id: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('prompt_versions') as batch_op:
        batch_op.drop_column('book_id')
        batch_op.drop_column('rollback_reason')
        batch_op.drop_column('score_after')
        batch_op.drop_column('score_before')

