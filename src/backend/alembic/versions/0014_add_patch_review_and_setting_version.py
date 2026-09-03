"""add patch_reviews, setting_deltas, setting_versions tables and audit_issue review fields

Revision ID: 0014_add_patch_review_and_setting_version
Revises: 0013_graph_pipeline_idempotency
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_add_patch_review_and_setting_version"
down_revision = "0013_graph_pipeline_idempotency"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # NOTE: audit_issues columns (patch_review_id, user_resolution, resolved_at, resolved_by)
    # are already created by Base.metadata.create_all() from the model definition.
    # This migration only creates the new tables.

    # Create patch_reviews table
    if not _table_exists("patch_reviews"):
        op.create_table(
            "patch_reviews",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("ep_num", sa.Integer(), nullable=False),
            sa.Column("patch_type", sa.String(50), nullable=False),
            sa.Column("original_content", sa.Text(), nullable=False),
            sa.Column("proposed_content", sa.Text(), nullable=False),
            sa.Column("diff_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(20), nullable=False, server_default="generated"),
            sa.Column("reviewer_id", sa.String(100), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=False, server_default=""),
            sa.Column("audit_issue_ids", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("learning_metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column(
                "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
            ),
        )
        op.create_index("idx_patch_reviews_book_ep", "patch_reviews", ["book_id", "ep_num"])
        op.create_index("idx_patch_reviews_status", "patch_reviews", ["status"])

    # Create setting_deltas table
    if not _table_exists("setting_deltas"):
        op.create_table(
            "setting_deltas",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("field_path", sa.String(500), nullable=False),
            sa.Column("old_value", sa.Text(), nullable=True),
            sa.Column("new_value", sa.Text(), nullable=True),
            sa.Column("delta_type", sa.String(50), nullable=False),
            sa.Column("source", sa.String(50), nullable=False),
            sa.Column("merged_to_graphrag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("merged_at", sa.DateTime(), nullable=True),
            sa.Column(
                "patch_review_id", sa.Integer(), sa.ForeignKey("patch_reviews.id"), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("idx_setting_deltas_book_field", "setting_deltas", ["book_id", "field_path"])
        op.create_index("idx_setting_deltas_merged", "setting_deltas", ["merged_to_graphrag"])

    # Create setting_versions table with unique constraint
    if not _table_exists("setting_versions"):
        op.create_table(
            "setting_versions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("snapshot_json", sa.Text(), nullable=False),
            sa.Column(
                "base_version_id", sa.Integer(), sa.ForeignKey("setting_versions.id"), nullable=True
            ),
            sa.Column("change_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("book_id", "version_number", name="uq_setting_versions_book_ver"),
        )
        op.create_index("idx_setting_versions_book", "setting_versions", ["book_id"])


def downgrade() -> None:
    if _table_exists("setting_versions"):
        op.drop_table("setting_versions")

    if _table_exists("setting_deltas"):
        op.drop_table("setting_deltas")

    if _table_exists("patch_reviews"):
        op.drop_table("patch_reviews")

    # Note: audit_issues columns are managed by the model, not removed here