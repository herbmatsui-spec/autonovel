"""0027_multitenancy_users.py

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_multitenancy_users"
down_revision = "0026_audio_assets"
branch_labels = None
depends_on = None


def upgrade():
    # ユーザーテーブルの作成
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("plan_tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 既存テーブルへの user_id 追加
    # SQLiteの制約上、直接的にForeignKeyをALTERで追加するのは難しいが、Alembicがhandleしてくれる場合が多い
    op.add_column("books", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("idx_books_user_id", "books", ["user_id"])
    
    op.add_column("branches", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("idx_branches_user_id", "branches", ["user_id"])
    
    op.add_column("chapters", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("idx_chapters_user_id", "chapters", ["user_id"])


def downgrade():
    op.drop_index("idx_chapters_user_id", table_name="chapters")
    op.drop_column("chapters", "user_id")
    op.drop_index("idx_branches_user_id", table_name="branches")
    op.drop_column("branches", "user_id")
    op.drop_index("idx_books_user_id", table_name="books")
    op.drop_column("books", "user_id")
    op.drop_table("users")
