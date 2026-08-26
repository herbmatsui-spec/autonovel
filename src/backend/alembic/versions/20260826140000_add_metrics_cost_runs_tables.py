"""add metrics cost runs tables

Revision ID: 20260826140000
Revises: 19641492fe26
Create Date: 2026-08-26 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20260826140000'
down_revision = '19641492fe26'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # narrative_metrics
    op.create_table(
        'narrative_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chapter_id', sa.Integer(), sa.ForeignKey('chapters.id', ondelete='CASCADE'), nullable=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_narrative_metrics_book_id', 'narrative_metrics', ['book_id'])
    op.create_index('idx_narrative_metrics_chapter_id', 'narrative_metrics', ['chapter_id'])
    op.create_index('idx_narrative_metrics_metric_name', 'narrative_metrics', ['metric_name'])

    # cost_records
    op.create_table(
        'cost_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id', ondelete='CASCADE'), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False, default=1),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('output_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('total_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('est_cost_usd', sa.Float(), nullable=False, default=0.0),
        sa.Column('ep_num', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_cost_record_book_id', 'cost_records', ['book_id'])
    op.create_index('idx_cost_record_branch_id', 'cost_records', ['branch_id'])

    # generation_runs
    op.create_table(
        'generation_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chapter_ep', sa.Integer(), nullable=True),
        sa.Column('task_type', sa.String(50), nullable=False, default='writing'),
        sa.Column('prompt_version', sa.String(100), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('params_json', sa.Text(), nullable=True),
        sa.Column('input_hash', sa.String(64), nullable=True),
        sa.Column('output_preview', sa.Text(), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_generation_run_book_id', 'generation_runs', ['book_id'])
    op.create_index('idx_generation_run_chapter_ep', 'generation_runs', ['chapter_ep'])


def downgrade() -> None:
    op.drop_index('idx_generation_run_chapter_ep', table_name='generation_runs')
    op.drop_index('idx_generation_run_book_id', table_name='generation_runs')
    op.drop_table('generation_runs')
    op.drop_index('idx_cost_record_branch_id', table_name='cost_records')
    op.drop_index('idx_cost_record_book_id', table_name='cost_records')
    op.drop_table('cost_records')
    op.drop_index('idx_narrative_metrics_metric_name', table_name='narrative_metrics')
    op.drop_index('idx_narrative_metrics_chapter_id', table_name='narrative_metrics')
    op.drop_index('idx_narrative_metrics_book_id', table_name='narrative_metrics')
    op.drop_table('narrative_metrics')