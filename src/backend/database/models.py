from __future__ import annotations

"""
database/models.py - SQLAlchemy ORMモデル定義
全テーブルの宣言的マッピングを集約。
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Engine event listener for SQLite WAL mode (applied in core.py via DatabaseManager)
@event.listens_for(Base.metadata, "after_create")
def on_create(target, connection, **kw):
    if "sqlite" in str(connection.engine.name):
        connection.execute(text("PRAGMA journal_mode=WAL;"))
        connection.execute(text("PRAGMA foreign_keys=ON;"))


# ==========================================
# Core tables
# ==========================================

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    genre = Column(String(100), default="")
    concept = Column(Text, default="")
    synopsis = Column(Text, default="")
    catchcopy = Column(String(255), default="")
    target_eps = Column(Integer, default=50)
    style_dna = Column(Text, default="")
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, server_default=func.now())
    marketing_data = Column(Text, default="")
    cumulative_tension = Column(Integer, default=0)
    cumulative_qol = Column(Integer, default=0)
    cumulative_cost = Column(Float, default=0.0)
    sanctuary_integrity = Column(Integer, default=100)
    current_branch_id = Column(Integer, nullable=True)


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, nullable=True)
    fork_ep_num = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Bible(Base):
    __tablename__ = "bibles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    settings = Column(Text, default="")
    revealed = Column(Text, default="")
    version = Column(Integer, default=1)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BiblePendingSetting(Base):
    __tablename__ = "bible_pending_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    proposed_value = Column(Text, default="")
    confidence = Column(Float, default=0.0)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, server_default=func.now())


class Plot(Base):
    __tablename__ = "plots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_tension = Column(Float, nullable=True, comment="動的に計算された目標テンション値 (0.0-1.0)")
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, default=1, nullable=False)
    ep_num = Column(Integer, nullable=False)
    thought_process = Column(Text, default="")
    title = Column(String(200))
    summary = Column(Text)
    detailed_blueprint = Column(Text, default="")
    tension = Column(Integer, default=50)
    tension_delta = Column(Integer, default=0)
    catharsis = Column(Integer, default=0)
    status = Column(String(50), default="planned")
    scenes = Column(Text, default="[]")
    is_catharsis = Column(Boolean, default=False)
    catharsis_type = Column(String(50), default="なし")
    love_meter = Column(Integer, default=0)
    next_hook = Column(Text, default="{}")
    misunderstanding_gap = Column(Text, default="")
    lite_model_director_notes = Column(Text, default="")
    script_content = Column(Text, default="")
    current_chain_phase = Column(String(50), default="Friction")
    resolution_style = Column(String(50), default="Cheat")
    burned_cost_or_loot = Column(String(100), default="なし")
    antagonist_status = Column(String(100), default="現状維持")
    thematic_milestone = Column(String(100), default="なし")
    state_integrity_score = Column(Integer, default=100)
    emotional_resonance_score = Column(Integer, default=0)
    thematic_depth_score = Column(Integer, default=0)
    literary_beauty_score = Column(Integer, default=0)
    erotic_intensity = Column(Integer, default=0)
    healed_fields = Column(Text, default="[]")
    is_micro_catharsis = Column(Boolean, default=False)
    information_asymmetry_level = Column(Float, default=0.0)
    cost_score = Column(Float, default=0.0)
    qol_delta = Column(Integer, default=0)
    discovery_item = Column(Text)
    sanctuary_event = Column(Text)
    is_locked = Column(Boolean, default=False)
    is_simulation = Column(Boolean, default=False)
    simulation_id = Column(String, server_default="", nullable=True)
    pov_character_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("book_id", "branch_id", "ep_num", name="uq_plots_book_branch_ep"),
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, default=1, nullable=False)
    ep_num = Column(Integer, nullable=False)
    title = Column(String(200))
    content = Column(Text)
    score_story = Column(Integer)
    killer_phrase = Column(String(500))
    summary = Column(Text)
    world_state = Column(Text)
    trinity_review_log = Column(Text)
    ai_insight = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    tension_delta = Column(Integer, default=0)
    qol_delta = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("book_id", "branch_id", "ep_num", name="uq_chapters_book_branch_ep"),
    )


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100))
    role = Column(String(50))
    registry_data = Column(Text)


class CharacterArc(Base):
    __tablename__ = "character_arcs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    arc_name = Column(String(100))
    arc_stages = Column(Text, default="[]")
    current_stage_index = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Foreshadowing(Base):
    __tablename__ = "foreshadowing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, default=1, nullable=False)
    ep_num = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text)
    location = Column(String(100))
    payoff_ep = Column(Integer, nullable=True)
    payoff_location = Column(String(100), nullable=True)
    strength = Column(Float, default=1.0)
    fulfilled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("book_id", "branch_id", "ep_num", "type", name="uq_foreshadowing"),
    )


# ==========================================
# Outbox / ChromaDB sync
# ==========================================

class Outbox(Base):
    __tablename__ = "outbox"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)


# ==========================================
# Prompt management
# ==========================================

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=True)
    prompt_key = Column(String(100), nullable=False)
    version_tag = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    score_before = Column(Float)
    score_after = Column(Float)
    ab_test_metrics = Column(Text, default="{}")
    rollback_reason = Column(String(255))
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class PromptUsageLog(Base):
    __tablename__ = "prompt_usage_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    template_name = Column(String(255), nullable=False, index=True)
    hits = Column(Integer, nullable=False, default=0)
    total_time_ms = Column(Float, nullable=False, default=0.0)
    avg_time_ms = Column(Float, nullable=False, default=0.0)
    last_accessed = Column(DateTime, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_prompt_usage_timestamp", "timestamp"),
        Index("idx_prompt_usage_template", "template_name"),
    )


# ==========================================
# Rules & Mastering
# ==========================================

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_word = Column(String(200), nullable=False)
    instruction = Column(Text, nullable=False)
    level = Column(String(50), default="global")
    domain = Column(String(50), default="all")
    character_name = Column(String(100))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Masterpiece(Base):
    __tablename__ = "masterpieces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emotion_or_scene = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    vector_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ==========================================
# Audit
# ==========================================

class AuditIssue(Base):
    __tablename__ = "audit_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    ep_num = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    evidence_past = Column(Text, default="")
    evidence_current = Column(Text, default="")
    constraint_for_next_ep = Column(Text, default="")
    status = Column(String(20), default="open")
    resolved_note = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


# ==========================================
# Misc / Utility tables
# ==========================================

class OptimizationHistory(Base):
    __tablename__ = "optimization_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    report_json = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())


class StyleFragment(Base):
    __tablename__ = "style_fragments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text)
    origin = Column(String(50), default="Master")
    created_at = Column(DateTime, server_default=func.now())


class CustomStyle(Base):
    __tablename__ = "custom_styles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    instruction = Column(Text)
    score = Column(Integer, default=0)
    analysis = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class InternalState(Base):
    __tablename__ = "internal_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), nullable=False, unique=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PendingPatch(Base):
    __tablename__ = "pending_patches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    patch_type = Column(String(50), nullable=False)
    patch_content = Column(Text, nullable=False)
    ab_test_result = Column(Text, default="{}")
    status = Column(String(20), default="pending")
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(String(64), primary_key=True)
    status = Column(String(20), default="running")
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    message = Column(String(500), default="")
    sub_message = Column(String(500), default="")
    streaming_text = Column(Text, default="")
    logs = Column(Text, default="[]")
    error = Column(Text)
    result_data = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NarrativeMetric(Base):
    __tablename__ = "narrative_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_narrative_metrics_book_id", "book_id"),
        Index("idx_narrative_metrics_chapter_id", "chapter_id"),
        Index("idx_narrative_metrics_metric_name", "metric_name"),
    )


class EntertainmentCheckLog(Base):
    __tablename__ = "entertainment_check_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    ep_num = Column(Integer, nullable=False)
    interest_score = Column(Integer, nullable=True)
    physiological_reaction = Column(String(255), nullable=True)
    would_continue_reading = Column(Boolean, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_entertainment_check_log_book_ep", "book_id", "ep_num"),
    )
