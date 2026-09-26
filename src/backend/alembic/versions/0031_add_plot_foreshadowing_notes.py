"""add foreshadowing_notes to plots

Revision ID: 0031_plot_foreshadowing_notes
Revises: 0030_add_foreshadowing_scope
Create Date: 2026-09-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0031_plot_foreshadowing_notes"
down_revision = "0030_add_foreshadowing_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plots",
        sa.Column("foreshadowing_notes", sa.Text(), nullable=True, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("plots", "foreshadowing_notes")

