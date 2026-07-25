# AutoNovel v3.0 詳細実装計画書 (72ステップ + 統合)

## 1. システム概要とデータフロー

```
【AutoNovel 覇権小説生成エンジン v3.0】

┌─────────────────────────────────────────────────────────────────────┐
│                        ユーザーインターフェース層                      │
│  Streamlit App (streamlit_app/)                                      │
│  ├── UIControllerManager                                            │
│  ├── UIEventBus + Stores (JobStore, SessionStore, ToastStore)       │
│  └── Controllers (PlanningCtrl, WritingCtrl, SystemCtrl)            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ UIEventType events
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     バックエンドサービス層                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ PlotAgent    │  │MarketingAgent│  │ WritingServices│             │
│  │ (プロット生成)│  │ (マーケティング)│  │ (執筆サービス) │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │
│         │                │                │                          │
│  ┌──────▼────────────────▼────────────────▼───────┐                │
│  │              LLMService (Gemini/OpenAI)         │                │
│  │  - resolve_model() → 目的別モデル選択            │                │
│  │  - generate_json() → 構造化生成                  │                │
│  │  - generate_text() → テキスト生成                │                │
│  └──────┬───────────────────────────────────────────┘                │
└─────────┼───────────────────────────────────────────────────────────┘
          │ async calls
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      スタイルRAG引擎                                  │
│  StyleRagManager                                                      │
│  ├── _get_embedding() → Gemini埋め込み生成                            │
│  ├── find_best_samples() → コサイン類似度検索                        │
│  ├── add_master_fragment() → 文体サンプル登録                        │
│  └── format_as_prompt() → プロンプト整形                             │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      データベース層 (SQLAlchemy + SQLite)             │
│  UnitOfWork                                                          │
│  ├── BookRepository                                                  │
│  ├── PlotRepository                                                  │
│  ├── ChapterRepository                                               │
│  ├── CharacterRepository                                             │
│  ├── BibleRepository (世界設定・Bible管理)                           │
│  ├── AuditRepository (論理矛盾監査)                                 │
│  └── Outbox (ChromaDB同期)                                          │
│                                                                      │
│  【主要テーブル】                                                    │
│  books, branches, bibles, plots, chapters, characters,              │
│  audit_issues, foreshadowing, style_fragments, narrative_metrics    │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 完全なインターフェースと型定義

```python
# === 言語・フレームワーク ===
# Python 3.12+ / Pydantic V2 / SQLAlchemy 2.0 (Async) / Streamlit

# ============================================================
# 2.1 データ転送オブジェクト (DTO)
# ============================================================

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

class StoryDNADTO(BaseModel):
    core_concept: str = ""
    mc_immutable_core: str = ""
    world_laws: str = ""
    climax_vision: str = ""
    marketing_hooks: List[str] = Field(default_factory=list)
    mutation_history: List[str] = Field(default_factory=list)
    version: int = 1

class MarketingAssetsDTO(BaseModel):
    catchcopies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    ab_test_candidates: List[Dict[str, Any]] = Field(default_factory=list)

class WorldRulesDTO(BaseModel):
    magic_cost_and_taboo: str = "なし"
    social_hierarchy_and_discrimination: str = "なし"
    hidden_truths: Dict[str, str] = Field(default_factory=dict)
    truth_ledger: Dict[str, Any] = Field(default_factory=dict)
    geopolitics_and_economy: str = "なし"
    religious_dogma_and_heresy: str = "なし"
    causality_map: List[str] = Field(default_factory=list)
    foreshadowing_map: List[Any] = Field(default_factory=list)
    active_constraints: List[Any] = Field(default_factory=list)
    climax_scenes: List[Any] = Field(default_factory=list)
    mystery_disclosure_schedule: List[Dict[str, Any]] = Field(default_factory=list)
    tension_threshold: int = 85
    tension_gain: float = 1.0
    memory_integrity_score: int = 100
    location_sensory_map: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    initial_qol_score: int = 0
    initial_sanctuary_integrity: int = 100

class CharacterRegistryDTO(BaseModel):
    name: str = ""
    role: str = ""
    gender: str = ""
    age: str = ""
    appearance: str = ""
    personality: str = ""
    surface_persona: str = ""
    inner_conflict: str = ""
    core_trauma: str = ""
    save_the_cat_event: str = ""
    first_person: str = "私"
    second_person: str = "貴方"
    suffix_style: str = ""
    suffix_patterns: List[str] = Field(default_factory=list)
    known_facts: List[str] = Field(default_factory=list)
    unknown_facts: List[str] = Field(default_factory=list)
    ability: str = ""
    background: str = ""
    tone: str = ""
    iron_constraint: str = ""
    fate_link: str = ""
    social_mask_vs_truth: str = ""
    pronouns: Dict[str, str] = Field(default_factory=dict)
    relationships: List[Any] = Field(default_factory=list)
    dialogue_samples: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    expansion_hooks: List[str] = Field(default_factory=list)

class ArcBlueprintDTO(BaseModel):
    arc_num: int
    start_ep: int
    end_ep: int
    title: str = "無題"
    summary: str = ""

class RoadmapItemDTO(BaseModel):
    ep_num: int
    one_line_summary: str
    resolution_style: Literal["Cheat", "Logic", "Focus_Drama"]
    burned_cost_or_loot: str = "なし"
    thematic_milestone: str = "なし"
    antagonist_status: str
    is_catharsis: bool = False
    foreshadowing_setup: str = "なし"
    foreshadowing_payoff: str = "なし"

class PlotCoreInfoDTO(BaseModel):
    ep_num: int = 0
    thought_process: str = ""
    title: str = ""
    one_line_summary: str = ""
    detailed_blueprint: str = ""

class PlotAnalyticsDTO(BaseModel):
    tension: int = 50
    tension_delta: int = 0
    catharsis: int = 0
    is_catharsis: bool = False
    love_meter: int = 0
    catharsis_type: str = "なし"
    emotional_payoff: str = ""
    resolution_style: str = "Cheat"
    antagonist_status: str = "現状維持"
    state_integrity_score: int = 100
    emotional_hook: Optional[Any] = None
    sharp_edges: List[Any] = Field(default_factory=list)
    quality_polish_status: Literal["pending", "passed", "rejected_edge_loss"] = "pending"

class PlotEpisodeDTO(BaseModel):
    core_info: PlotCoreInfoDTO = Field(default_factory=PlotCoreInfoDTO)
    analytics: PlotAnalyticsDTO = Field(default_factory=PlotAnalyticsDTO)
    foreshadowing: Any = Field(default_factory=dict)
    next_hook: Any = None
    misunderstanding_gap: str = ""
    scenes: List[Any] = Field(default_factory=list)
    script_content: str = ""
    current_chain_phase: str = "Friction"
    burned_cost_or_loot: str = "なし"
    thematic_milestone: str = "なし"
    healed_fields: List[str] = Field(default_factory=list)
    is_micro_catharsis: bool = False
    information_asymmetry_level: float = 0.0
    lite_model_director_notes: str = ""
    emotional_resonance_score: int = 0
    thematic_depth_score: int = 0
    literary_beauty_score: int = 0
    extra_engines: Dict[str, Any] = Field(default_factory=dict)

    @property
    def ep_num(self) -> int:
        return self.core_info.ep_num

    @property
    def title(self) -> str:
        return self.core_info.title

    @property
    def detailed_blueprint(self) -> str:
        return self.core_info.detailed_blueprint

    @property
    def tension(self) -> int:
        return self.analytics.tension

    @property
    def is_catharsis(self) -> bool:
        return self.analytics.is_catharsis

# ============================================================
# 2.2 ユースケース入力モデル
# ============================================================

class CreateBookInput(BaseModel):
    title: str
    genre: str = "ファンタジー"
    concept: str = ""
    synopsis: str = ""
    target_eps: int = 50
    style_key: str = "style_web_standard"
    keywords: str = ""
    mc_profile: CharacterRegistryDTO = Field(default_factory=CharacterRegistryDTO)
    sub_characters: List[CharacterRegistryDTO] = Field(default_factory=list)
    world_settings: WorldRulesDTO = Field(default_factory=WorldRulesDTO)

class GenerateEpisodeInput(BaseModel):
    book_id: int
    ep_num: int
    target_word_count: int = 2000
    enable_polishing: bool = True
    is_easy_mode: bool = False

class ExpandPlotsInput(BaseModel):
    book_id: int
    ep_nums: List[int]
    arcs: List[ArcBlueprintDTO]
    force: bool = False
    branch_id: Optional[int] = None

class RebuildPlotInput(BaseModel):
    book_id: int
    start_ep: int
    new_total_eps: int
    keywords: str = ""
    trend_memo: str = ""
    plot_pattern_key: str = ""
    cost_severity: int = 50
    cheat_scale: int = 50
    system_assist: int = 50

class MarketingPackInput(BaseModel):
    book_title: str
    synopsis: str
    latest_ep: int

class ExportPackageInput(BaseModel):
    book_id: int

# ============================================================
# 2.3 リポジトリインターフェース
# ============================================================

from typing import Protocol, AsyncIterator

class IRepository(Protocol):
    async def update_plot_blueprint(self, book_id: int, blueprint: str) -> bool: ...
    async def create_book(self, book_data: Dict[str, Any]) -> int: ...
    async def save_plot(self, branch_id: int, ep_num: int, plot: Any) -> bool: ...
    async def get_book(self, book_id: int) -> Optional[Any]: ...
    async def get_all_plots(self, book_id: int, branch_id: int = 1) -> List[Any]: ...
    async def get_latest_bible(self, book_id: int) -> Optional[Any]: ...
    async def get_all_characters(self, book_id: int) -> List[Any]: ...
    async def get_all_non_anchor_chapters(self, book_id: int, branch_id: int, order_by: str) -> List[Any]: ...
    async def get_plots_between(self, branch_id: int, start_ep: int, end_ep: int) -> List[Any]: ...

class BookRepositoryProtocol(Protocol):
    async def create(self, title: str, genre: str, concept: str, synopsis: str, target_eps: int, style_dna: str, marketing_data: str) -> int: ...
    async def get_by_id(self, book_id: int) -> Optional[Any]: ...
    async def update(self, book_id: int, **kwargs) -> bool: ...
    async def list_all(self) -> List[Any]: ...

class PlotRepositoryProtocol(Protocol):
    async def save(self, branch_id: int, ep_num: int, plot_data: Any) -> bool: ...
    async def get_by_episode(self, book_id: int, branch_id: int, ep_num: int) -> Optional[Any]: ...
    async def get_range(self, book_id: int, branch_id: int, start_ep: int, end_ep: int) -> List[Any]: ...
    async def archive_plots_from(self, branch_id: int, start_ep: int, new_total: int) -> None: ...
    async def delete_plots_from(self, branch_id: int, start_ep: int) -> None: ...

class ChapterRepositoryProtocol(Protocol):
    async def create(self, book_id: int, branch_id: int, ep_num: int, title: str, content: str, summary: str, world_state: str, tension_delta: int, qol_delta: int) -> int: ...
    async def get_by_episode(self, book_id: int, branch_id: int, ep_num: int) -> Optional[Any]: ...
    async def update_content(self, chapter_id: int, content: str, summary: str, world_state: str, tension_delta: int, qol_delta: int) -> bool: ...

class CharacterRepositoryProtocol(Protocol):
    async def create(self, book_id: int, name: str, role: str, registry_data: str) -> int: ...
    async def get_by_book(self, book_id: int) -> List[Any]: ...
    async def update_registry(self, character_id: int, registry_data: str) -> bool: ...

class BibleRepositoryProtocol(Protocol):
    async def create_bible(self, book_id: int, settings: Any, version: int, last_updated: str) -> None: ...
    async def get_latest_bible(self, book_id: int) -> Optional[Any]: ...
    async def save_full_world_bible(self, bible: Any, **kwargs) -> int: ...

class AuditRepositoryProtocol(Protocol):
    async def save_issue(self, book_id: int, ep_num: int, category: str, severity: str, description: str, evidence_past: str, evidence_current: str, constraint_for_next_ep: str) -> int: ...
    async def get_open_issues(self, book_id: int, ep_num: int) -> List[Any]: ...
    async def resolve_issue(self, issue_id: int, resolved_note: str) -> bool: ...

# ============================================================
# 2.4 エージェントインターフェース
# ============================================================

class IPlotExpander(Protocol):
    async def expand_single_plot(self, book_id: int, ep_num: int, arc_metadata: Dict[str, Any], past_context: str, world_settings: str, reporter: Optional[Any], expected_ep_num: Optional[int], system_overrides: Optional[Dict[str, Any]]) -> PlotEpisodeDTO: ...
    async def expand_plots(self, book_id: int, target_ep_list: List[int], arcs: List[ArcBlueprintDTO], reporter: Optional[Any], force: bool, branch_id: Optional[int]) -> List[Any]: ...

class IPromptManager(Protocol):
    async def build_expansion_prompt(self, book_title: str, ep_num: int, arc_metadata: Dict[str, Any], past_context: str, world_settings: str, system_overrides: Optional[Dict[str, Any]]) -> str: ...
    async def build_beat_expansion_prompt(self, blueprint: str, book_id: Optional[int]) -> str: ...
    async def build_polishing_prompt(self, draft_content: str, target_word_count: int, style_key: str, prose_sample: str, plot_data: Optional[Dict[str, Any]], use_beat_rules: bool, book_id: Optional[int]) -> str: ...
    async def build_critic_feedback_prompt(self, issue_list: Any, draft_content: str, blueprint: str) -> str: ...
    async def build_surgical_causality_healing_prompt(self, target_content: str, world_settings: str, blueprint: str, failure_reason: str) -> str: ...
    async def build_marketing_pack_prompt(self, book_title: str, synopsis: str, latest_ep: int, **kwargs) -> str: ...

class IReporter(Protocol):
    def report(self, message: str, level: str) -> None: ...
    def update_progress(self, current: int, total: int, message: str) -> None: ...
    def update_streaming_text(self, text: str) -> None: ...

# ============================================================
# 2.5 サービスレジデンス
# ============================================================

class StyleRagConfig(BaseModel):
    embedding_model: str = "gemini-embedding-2"
    top_k: int = 2
    similarity_threshold: float = 0.5
    cache_size: int = 1000

class WritingServiceConfig(BaseModel):
    model_writing: str = "gemini-2.0-flash"
    model_audit: str = "gemini-2.0-flash"
    actor_critic_max_iterations: int = 2
    actor_critic_enabled: bool = True
    actor_critic_severity_threshold: str = "Critical"
    fail_fast_mode: bool = False
    draft_polish_enabled: bool = True
    polishing_min_content_ratio: float = 0.5
    min_immersion_score: float = 0.0

class LLMServiceConfig(BaseModel):
    api_key: Optional[str] = None
    temperature_default: float = 0.7
    max_retries: int = 5
    timeout_seconds: float = 60.0

# ============================================================
# 2.6 データベーススキーマ対応Pythonモデル
# ============================================================

from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class BookModel(Base):
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
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    marketing_data = Column(Text, default="")
    cumulative_tension = Column(Integer, default=0)
    cumulative_qol = Column(Integer, default=0)
    cumulative_cost = Column(Float, default=0.0)
    sanctuary_integrity = Column(Integer, default=100)
    current_branch_id = Column(Integer, nullable=True)

class PlotModel(Base):
    __tablename__ = "plots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_tension = Column(Float, nullable=True)
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
    is_micro_catharsis = Column(Boolean, default=False)
    information_asymmetry_level = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("book_id", "branch_id", "ep_num", name="uq_plots_book_branch_ep"),
    )

class ChapterModel(Base):
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
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    tension_delta = Column(Integer, default=0)
    qol_delta = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("book_id", "branch_id", "ep_num", name="uq_chapters_book_branch_ep"),
    )

class CharacterModel(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100))
    role = Column(String(50))
    registry_data = Column(Text)

class BibleModel(Base):
    __tablename__ = "bibles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    settings = Column(Text, default="")
    revealed = Column(Text, default="")
    version = Column(Integer, default=1)
    last_updated = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

class AuditIssueModel(Base):
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
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class NarrativeMetricModel(Base):
    __tablename__ = "narrative_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("idx_narrative_metrics_book_id", "book_id"),
        Index("idx_narrative_metrics_chapter_id", "chapter_id"),
        Index("idx_narrative_metrics_metric_name", "metric_name"),
    )

class StyleFragmentModel(Base):
    __tablename__ = "style_fragments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text)
    origin = Column(String(50), default="Master")
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class BranchModel(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, nullable=True)
    fork_ep_num = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class ForeshadowingModel(Base):
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
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        UniqueConstraint("book_id", "branch_id", "ep_num", "type", name="uq_foreshadowing"),
    )

class InternalStateModel(Base):
    __tablename__ = "internal_state"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), nullable=False, unique=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

class BackgroundTaskModel(Base):
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
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
```

## 3. エッジケースと例外処理の要件定義

```python
"""
【例外クラス階層】

BaseException
├── EngineError (基底例外)
│   ├── ValidationError: 入力バリデーション失敗
│   ├── RepositoryError: データアクセスエラー
│   ├── LLMServiceError: LLM API エラー
│   │   ├── LLMTimeoutError: タイムアウト
│   │   ├── LLMQuotaError: 配额超過
│   │   └── LLMAPIError: API エラー
│   ├── PlotGenerationError: プロット生成失敗
│   ├── WritingGenerationError: 執筆生成失敗
│   ├── AuditError: 監査処理エラー
│   ├── BibleNotFoundError: Bible 未検出
│   ├── BookNotFoundError: 作品未検出
│   ├── PlotNotFoundError: プロット未検出
│   ├── CharacterNotFoundError: キャラクター未検出
│   ├── ChromaDBError: ChromaDB 同期エラー
│   └── ConfigurationError: 設定エラー
"""

class EngineError(Exception):
    """エンジン基底例外"""
    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)

class ValidationError(EngineError):
    """入力バリデーション失敗"""
    pass

class RepositoryError(EngineError):
    """データアクセスエラー"""
    pass

class LLMServiceError(EngineError):
    """LLM API エラー基底"""
    pass

class LLMTimeoutError(LLMServiceError):
    """タイムアウト (発生条件: 60秒以上応答なし)"""
    pass

class LLMQuotaError(LLMServiceError):
    """配额超過 (発生条件: API quota 403/429)"""
    pass

class LLMAPIError(LLMServiceError):
    """API エラー (発生条件: 4xx/5xx レスポンス)"""
    pass

class PlotGenerationError(EngineError):
    """プロット生成失敗"""
    pass

class WritingGenerationError(EngineError):
    """執筆生成失敗"""
    pass

class AuditError(EngineError):
    """監査処理エラー"""
    pass

class BibleNotFoundError(EngineError):
    """Bible 未検出 (発生条件: get_latest_bible() が None を返す)"""
    pass

class BookNotFoundError(EngineError):
    """作品未検出 (発生条件: get_book() が None を返す)"""
    pass

class PlotNotFoundError(EngineError):
    """プロット未検出 (発生条件: 指定話数のプロットが存在しない)"""
    pass

class CharacterNotFoundError(EngineError):
    """キャラクター未検出"""
    pass

class ChromaDBError(EngineError):
    """ChromaDB 同期エラー"""
    pass

class ConfigurationError(EngineError):
    """設定エラー"""
    pass

# ============================================================
# 3.1 例外処理マッピング表
# ============================================================

EXCEPTION_HANDLING_TABLE = {
    ValidationError: {
        "Detection": "Pydantic バリデーションエラー (ValidationError)",
        "Handling": "400 Bad Request を返り、入力パラメータのエラー内容を通知",
        "Logging": "WARNING レベルで入力値とバリデーションエラーを記録",
    },
    RepositoryError: {
        "Detection": "SQLAlchemy 例外 (SQLAlchemyError, OperationalError)",
        "Handling": "トランザクションをロールバックし、500 Internal Server Error を返す",
        "Logging": "ERROR レベルで SQL エラーとスタックトレースを記録",
    },
    LLMTimeoutError: {
        "Detection": "asyncio.TimeoutError, httpx.TimeoutException",
        "Handling": "リトライ3回、それでも失敗時はフォールバックサンプルを返り執筆を続行",
        "Logging": "WARNING レベルでタイムアウト時間とリトライ回数を記録",
    },
    LLMQuotaError: {
        "Detection": "ステータスコード 403, 429",
        "Handling": "1時間待機後にリトライ、5回失敗時は執筆をスキップして次の話へ",
        "Logging": "ERROR レベルで quota エラーと待機時間を記録",
    },
    LLMAPIError: {
        "Detection": "ステータスコード 4xx (403, 429以外), 5xx",
        "Handling": "リトライ5回 ( exponential backoff: 1s, 2s, 4s, 8s, 16s)",
        "Logging": "ERROR レベルでステータスコードとレスポンスボディを記録",
    },
    PlotGenerationError: {
        "Detection": "PlotAgent._expand_single_plot() が RuntimeError を送出",
        "Handling": "max_retries=3 で再試行、3回失敗時は空の PlotEpisode を返りスキップ",
        "Logging": "ERROR レベルでプロット生成エラーとブックID/話数を記録",
    },
    WritingGenerationError: {
        "Detection": "GenerationLoopManager.execute_generation_loop() が RuntimeError を送出",
        "Handling": "fail_fast_mode=True の場合は例外を再送出、False の場合は空文字を返り続行",
        "Logging": "ERROR レベルで執筆エラーとコンテキストを記録",
    },
    BibleNotFoundError: {
        "Detection": "get_latest_bible() の戻り値が None",
        "Handling": "ValueError を送出 (作成前に Bible が必ず存在必要があるため)",
        "Logging": "DEBUG レベルで Bible 未検出を記録",
    },
    BookNotFoundError: {
        "Detection": "get_book() の戻り値が None",
        "Handling": "ValueError を送出",
        "Logging": "INFO レベルで作品未検索を記録",
    },
    ChromaDBError: {
        "Detection": "ChromaOutboxService.flush() の例外",
        "Handling": "Outbox への記録は成功裡に保ち、後続のバックグラウンド処理でリトライ",
        "Logging": "ERROR レベルで ChromaDB エラーを記録",
    },
}

# ============================================================
# 3.2 リトライポリシー
# ============================================================

RETRY_POLICY = {
    "llm_api": {
        "max_attempts": 5,
        "base_delay": 1.0,
        "max_delay": 16.0,
        "exponential_base": 2.0,
        "jitter": True,
    },
    "database": {
        "max_attempts": 15,
        "base_delay": 0.1,
        "max_delay": 60.0,
        "exponential_base": 1.5,
        "jitter": False,
    },
    "chroma_sync": {
        "max_attempts": 3,
        "base_delay": 1.0,
        "max_delay": 10.0,
        "exponential_base": 2.0,
        "jitter": True,
    },
}

# ============================================================
# 3.3 入力バリデーションルール
# ============================================================

INPUT_VALIDATION_RULES = {
    "book_id": {"type": "int", "min": 1, "required": True},
    "ep_num": {"type": "int", "min": 1, "max": 9999, "required": True},
    "target_word_count": {"type": "int", "min": 100, "max": 50000, "default": 2000},
    "branch_id": {"type": "int", "min": 1, "default": 1},
    "title": {"type": "str", "min_length": 1, "max_length": 200},
    "genre": {"type": "str", "min_length": 1, "max_length": 100},
    "temperature": {"type": "float", "min": 0.0, "max": 2.0, "default": 0.7},
}

def validate_input(rules: Dict, input_data: Dict) -> Tuple[bool, List[str]]:
    """入力バリデーション共通関数"""
    errors = []
    for field, rule in rules.items():
        value = input_data.get(field)
        
        # Required check
        if rule.get("required", False) and (value is None or value == ""):
            errors.append(f"{field} は必須です")
            continue
            
        if value is None:
            continue
            
        # Type check
        expected_type = rule.get("type")
        if expected_type == "int" and not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                errors.append(f"{field} は整数である必要があります")
                continue
                
        if expected_type == "float" and not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                errors.append(f"{field} は数値である必要があります")
                continue
                
        # Range check
        if expected_type in ("int", "float"):
            if "min" in rule and value < rule["min"]:
                errors.append(f"{field} は {rule['min']} 以上の値である必要があります")
            if "max" in rule and value > rule["max"]:
                errors.append(f"{field} は {rule['max']} 以下の値である必要があります")
                
        # String length check
        if expected_type == "str":
            if "min_length" in rule and len(value) < rule["min_length"]:
                errors.append(f"{field} は {rule['min_length']} 文字以上である必要があります")
            if "max_length" in rule and len(value) > rule["max_length"]:
                errors.append(f"{field} は {rule['max_length']} 文字以下である必要があります")
                
    return len(errors) == 0, errors
```

## 4. ステップ・バイ・ステップの実装タスク分割

```markdown
# AutoNovel v3.0 詳細実装計画書 (72ステップ)

## フェーズ1: 基盤整備 (ステップ1-12)

### ステップ1: プロジェクト構造の整理
- 作成・修正ファイル: `pyproject.toml`, `mypy.ini`, `pytest.ini`
- 実装関数: なし (設定ファイルのみ)
- 処理内容:
  - `pyproject.toml` の `[tool.mypy]` を `[mypy]` セクションに統合し、 `strict = true` を維持
  - `mypy.ini` を legacy として温存 (コメントで非推奨明記)
  - `pytest.ini` に `testpaths = autonovel/tests` を設定
  - `pythonpath = . autonovel autonovel/src` を追加

### ステップ2: Pydantic モデル統合モジュールの作成
- 作成ファイル: `src/models/__init__.py`
- 実装内容:
  ```python
  from src.models.audit import *
  from src.models.base import *
  from src.models.beat_sheet import *
  from src.models.bible import *
  from src.models.character import *
  from src.models.db import *
  from src.models.marketing import *
  from src.models.planning_config import *
  from src.models.plot import *
  from src.models.prompt_version import *
  from src.models.world import *
  from src.models.writing import *
  ```

### ステップ3: 例外クラス階層の定義
- 作成ファイル: `src/core/exceptions.py`
- 実装クラス:
  - `EngineError(Exception)` - 基底例外
  - `ValidationError(EngineError)` - 入力バリデーション
  - `RepositoryError(EngineError)` - データアクセス
  - `LLMServiceError(EngineError)` - LLM API 基底
  - `LLMTimeoutError(LLMServiceError)` - タイムアウト
  - `LLMQuotaError(LLMServiceError)` - quota 超過
  - `LLMAPIError(LLMServiceError)` - API エラー
  - `PlotGenerationError(EngineError)` - プロット生成
  - `WritingGenerationError(EngineError)` - 執筆生成
  - `BibleNotFoundError(EngineError)` - Bible 未検出
  - `BookNotFoundError(EngineError)` - 作品未検出
  - `ChromaDBError(EngineError)` - ChromaDB 同期

### ステップ4: リトライデコレータの実装
- 作成ファイル: `src/core/retry_decorator.py`
- 実装関数: `retry_with_logging(retries, base_delay, max_delay, exponential_base, jitter)`
- 処理内容:
  - 指定回数リトライ
  - exponential backoff (base_delay * (exponential_base ** i))
  - オプションでジッター追加
  - 各試行でログ出力
  - 最终失敗時のみ例外を再送出

### ステップ5: 設定アクセスLogger の構築
- 作成ファイル: `config/project_context.py`
- 実装クラス: `ProjectContext`
- 実装静的メソッド:
  - `get_setting(key, default)` → `get_config().{key}`
  - `set_setting(key, value)` → `setattr(config, key, value)` + TOML 永続化
  - `reset_overrides()` → `GlobalConfigModel.default()` 再設定

### ステップ6: データベース基盤の確認
- 作成・修正ファイル: `src/backend/database/core.py`
- 実装関数: `DatabaseManager`, `init_db()`, `get_db_manager()`
- 処理内容:
  - `create_async_engine()` による接続プール設定
  - SQLite 用の WAL モード、foreign keys、busy_timeout 設定
  - `get_session()` → `AsyncSession` 取得
  - `retry_with_logging` デコレータでラップ

### ステップ7: UnitOfWork 実装の確認
- 作成・修正ファイル: `src/backend/database/uow.py`
- 実装クラス: `UnitOfWork`
- 実装内容:
  - `__aenter__`: session 取得 + `current_uow.set(self)`
  - `__aexit__`: commit/rollback + ChromaDB outbox 同期
  - `stage_chroma_add()`, `stage_chroma_delete()` によるステージング
  - 各リポジトリへの委譲プロパティ (bible, books, plots, chapters, characters, etc.)

### ステップ8: リポジト_protoコル定義
- 作成ファイル: `src/backend/database/repo_protocols.py`
- 実装内容:
  ```python
  class IRepository(Protocol):
      async def update_plot_blueprint(self, book_id: str, blueprint: Any) -> bool: ...
      async def create_book(self, book_data: Any) -> str: ...
      async def save_plot(self, plot_data: Any) -> bool: ...
  ```

### ステップ9: BaseRepository 実装
- 作成ファイル: `src/backend/database/repositories/base.py`
- 実装クラス: `BaseRepository`
- 実装内容:
  - `_get_session()`: session プロパティ
  - `_to_dict()`: SQLAlchemy モデル → dict 変換
  - `_parse_row()`: 行データの正規化
  - 共通ユーティリティメソッド

### ステップ10: ブックリポジトリの実装
- 作成ファイル: `src/backend/database/repositories/book.py`
- 実装クラス: `BookRepository(BaseRepository)`
- 実装メソッド:
  - `create(title, genre, concept, synopsis, target_eps, style_dna, marketing_data) -> int`
  - `get_by_id(book_id) -> BookModel`
  - `update(book_id, **kwargs) -> bool`
  - `list_all() -> List[BookModel]`
  - `get_current_branch_id(book_id) -> int`

### ステップ11: プロットリポジトリの実装
- 作成ファイル: `src/backend/database/repositories/plot.py`
- 実装クラス: `PlotRepository(BaseRepository)`
- 実装メソッド:
  - `save(branch_id, ep_num, plot_data) -> bool`
  - `get_by_episode(book_id, branch_id, ep_num) -> PlotModel`
  - `get_range(book_id, branch_id, start_ep, end_ep) -> List[PlotModel]`
  - `get_all(book_id, branch_id) -> List[PlotModel]`
  - `archive_plots_from(branch_id, start_ep, new_total) -> None`
  - `delete_plots_from(branch_id, start_ep) -> None`

### ステップ12: 章リポジトリの実装
- 作成ファイル: `src/backend/database/repositories/chapter.py`
- 実装クラス: `ChapterRepository(BaseRepository)`
- 実装メソッド:
  - `create(book_id, branch_id, ep_num, title, content, summary, world_state, tension_delta, qol_delta) -> int`
  - `get_by_episode(book_id, branch_id, ep_num) -> ChapterModel`
  - `update_content(chapter_id, content, summary, world_state, tension_delta, qol_delta) -> bool`
  - `get_all_non_anchor(book_id, branch_id, order_by) -> List[ChapterModel]`

---

## フェーズ2: コアサービス基盤 (ステップ13-24)

### ステップ13: LLM サービス定義
- 作成ファイル: `src/services/llm_service.py`
- 実装クラス: `LLMService`
- 実装メソッド:
  - `__init__(api_key)` - API キー初期化
  - `_resolve_model(purpose) -> str` - 目的별モデル選択
  - `_ensure_factory() -> LLMProviderFactory`
  - `generate_json(purpose, prompt, response_schema, system_instruction, **kwargs) -> Dict[str, Any]`
  - `generate_text(purpose, prompt, system_instruction, **kwargs) -> str`

### ステップ14: LLM モデル選定ロジック
- 作成ファイル: `src/llm/model_router.py`
- 実装関数:
  - `select_model(purpose) -> str` - 目的별デフォルトモデル
  - `resolve_model(purpose) -> str` - モデル解決
- モデルマッピング:
  - planning → "gemini-2.0-flash"
  - plot_expansion → "gemini-2.0-flash"
  - writing → "gemini-2.0-flash"
  - climax → "gemini-2.0-flash"
  - audit → "gemini-2.0-flash"
  - marketing → "gemini-2.0-flash"

### ステップ15: プロンプトマネージャーインターフェース
- 作成ファイル: `src/services/prompt_manager.py`
- 実装クラス: `PromptManager`
- 実装メソッド:
  - `build_expansion_prompt(book_title, ep_num, arc_metadata, past_context, world_settings, system_overrides) -> str`
  - `build_beat_expansion_prompt(blueprint, book_id) -> str`
  - `build_polishing_prompt(draft_content, target_word_count, style_key, prose_sample, plot_data, use_beat_rules, book_id) -> str`
  - `build_critic_feedback_prompt(issue_list, draft_content, blueprint) -> str`
  - `build_surgical_causality_healing_prompt(target_content, world_settings, blueprint, failure_reason) -> str`
  - `build_marketing_pack_prompt(book_title, synopsis, latest_ep, **kwargs) -> str`
  - `build_fast_plot_screen_prompt(blueprint) -> str`
  - `build_ability_audit_prompt(blueprint, settings_json, characters_json) -> str`

### ステップ16: スタイル RAG マネージャー実装
- 作成ファイル: `src/backend/engine_style_rag.py`
- 実装クラス: `StyleRagManager`
- 実装メソッド:
  - `__init__(client, repo)` - client=LLMService, repo=Repository
  - `_get_embedding(text) -> List[float]` - Gemini 埋め込み生成 (キャッシュ付き)
  - `add_master_fragment(tag, content, origin) -> bool` - 文体サンプル登録
  - `find_best_sample(scene_description, phase, tag_hint, top_k) -> List[str]`
  - `find_best_samples(scene_description, phase, trope_hint, top_k) -> List[str]`
  - `_get_fallback_sample(phase) -> str` - フォールバックテンプレート
  - `format_as_prompt(samples) -> str` - プロンプト整形

### ステップ17: 執筆サービスの設定クラス
- 作成ファイル: `src/services/writing_services_config.py`
- 実装クラス: `WritingServiceConfig`
- フィールド:
  - `model_writing: str = "gemini-2.0-flash"`
  - `model_audit: str = "gemini-2.0-flash"`
  - `actor_critic_max_iterations: int = 2`
  - `actor_critic_enabled: bool = True`
  - `actor_critic_severity_threshold: str = "Critical"`
  - `fail_fast_mode: bool = False`
  - `draft_polish_enabled: bool = True`
  - `polishing_min_content_ratio: float = 0.5`
  - `min_immersion_score: float = 0.0`

### ステップ18: 執筆コンテキストモデル
- 作成ファイル: `src/models/writing.py` (既存拡張)
- 実装クラス:
  - `WritingGenerationContext(BaseModel)` - 執筆生成コンテキスト
    - `sys_inst: str`
    - `fw_prompt: str`
    - `pov_instruction: str`
    - `expanded_beats: str`
    - `feedback_patch: str`
    - `style_key: str`
    - `target_word_count: int`
    - `enable_polishing: bool`
    - `prose_sample: str`
    - `plot: Optional[Any]`
  - `EpisodeDraft(BaseModel)` - エピソード原案
  - `EpisodeMetadata(BaseModel)` - エピソードメタデータ
  - `EpisodeFinalDraft(BaseModel)` - 最終稿
  - `WritingContext(BaseModel)` - 執筆ワークフローコンテキスト

### ステップ19: GenerationLoopManager 核心実装
- 作成ファイル: `src/services/writing_services.py`
- 実装クラス: `GenerationLoopManager`
- 実装メソッド:
  - `execute_generation_loop(ep_num, ctx, sys_inst, fw_prompt, passion, is_easy_mode, reporter) -> Tuple[str, Dict[str, Any], bool]`
  - `_phase_prepare_context(...) -> Tuple[WritingGenerationContext, bool, bool, bool, int]`
  - `_phase_drafting(...) -> Tuple[str, Dict[str, Any]]`
  - `_phase_audit(...) -> Tuple[bool, float, bool, str, List[Dict[str, Any]]]`
  - `_phase_healing(...) -> Tuple[str, bool, str]`
  - `_phase_critic(...) -> bool`
  - `_determine_pov_instruction(ep_num, current_tension, is_catharsis, reporter) -> str`
  - `_calculate_ncs_score(ep_num, ctx) -> int`
  - `_expand_scene_beats(ep_num, blueprint, temp, reporter) -> str`
  - `_draft_episode_parts(ep_num, gen_ctx, temp, reporter) -> str`
  - `_polishing_pass(ep_num, draft_content, gen_ctx, temp, reporter, use_beat_rules) -> str`
  - `_extract_episode_metadata(ep_num, content, blueprint, temp) -> Dict[str, Any]`
  - `_run_causality_audits(...) -> Tuple[bool, str, List[Dict[str, Any]]]`
  - `_apply_surgical_healing(...) -> Tuple[str, bool, str]`
  - `_run_dogfeeding_loop(...) -> bool`
  - `_register_lazy_patch(...) -> None`

### ステップ20: 監査サービスの実装
- 作成ファイル: `src/agents/audit.py`
- 実装クラス:
  - `FastPlotScreener` - プロット快速スクリーニング
  - `AbilityConsistencyChecker` - 能力整合性チェック
  - `PlotIntegrityMonitor` - プロット整合性モニター
  - `DeAIAuditor` - AI感除去監査
  - `InternalLogicValidator` - 内部ロジック検証
  - `LogicalAuditor` - 論理一貫性チェック
    - `generate_critic_feedback(issue_list, draft_content, blueprint) -> CriticFeedback`
    - `audit_logical_consistency(book_id, ep_num, blueprint) -> Tuple[bool, str, float]`
    - `score_narrative_metrics(...) -> List[Dict[str, Any]]`
    - `analyze_tension_wave(book_id, ep_range) -> NarrativeWavePattern`

### ステップ21: 監査モデルの定義
- 作成ファイル: `src/models/audit.py` (既存拡張)
- 実装クラス:
  - `AuditIssue` - 1件の矛盾指摘
  - `LogicalAuditIssueList` - 監査結果リスト
  - `StoredAuditIssue` - DB永続化監査指摘
  - `CriticDirective` - Critic修正指令
  - `CriticFeedback` - Criticフィードバック全体
  - `ImmersionScore` - 感情没入スコア
  - `NarrativeWavePattern` - 物語波パター

### ステップ22: キャラクターagirの実装
- 作成ファイル: `src/models/character.py` (既存拡張)
- 実装クラス:
  - `CharacterConcept` - キャラクター初期コンセプト
  - `CharacterConceptList` - コンセプトリスト
  - `CharacterRelationship` - 関係性
  - `CharacterRegistry` - キャラクター登録情報 (Pydantic モデル)
    - `to_prompt()` → プロンプト文字列生成
    - `get_context_prompt(current_state)` → 詳細コンテキスト生成
    - `from_db(data)` → DB からの復元

### ステップ23: バイブルモデルの実装
- 作成ファイル: `src/models/bible.py` (既存拡張)
- 実装クラス:
  - `StoryDNA` - 物語DNA
  - `MarketingAssets` - マーケティング資産
  - `WorldBibleCore` - 世界Bibleコア
  - `WorldBible` - 世界設定Bible
  - `NovelStructure` - 小説構造
  - `UltraFastWorldBible` - 超高速生成用

### ステップ24: プロットモデルの実装
- 作成ファイル: `src/models/plot.py` (既存拡張)
- 実装クラス:
  - `PlotEpisode` - プロットエピソード
  - `PlotBlueprintPhase1` - Phase1設計図
  - `PlotCoreInfo` - プロット核心情報
  - `PlotAnalytics` - 分析情報
  - `ArcBlueprint` - アーク青写真
  - `RoadmapItem` - ロードマップ項目
  - `SceneBeat`, `SceneBeatBlock`, `MasterSceneBlock` - シーンビート
  - `CliffhangerDef` - cliffhanger 定義

---

## フェーズ3: エージェント実装 (ステップ25-36)

### ステップ25: PlotAgent 基本構造
- 作成ファイル: `src/agents/plot.py`
- 実装クラス: `PlotAgent`
- 初期化パラメータ:
  - `repo: IRepository`
  - `pm: IPromptManager`
  - `generate_json: Callable`
  - `plot_expander: Optional[IPlotExpander]`
  - `auditor: Optional[Any]`
  - `uow_factory: Optional[Callable]`

### ステップ26: PlotAgent _expand_single_plot 実装
- 対象ファイル: `src/agents/plot.py`
- 実装メソッド: `PlotAgent._expand_single_plot()`
- 処理内容:
  1. `_plot_expander.expand_single_plot()` を優先呼び出し
  2. 失敗時 `pm.build_expansion_prompt()` でプロンプト生成
  3. `generate_json()` で PlotEpisode 生成
  4. `RuntimeError` を送出する失敗条件の明示

### ステップ27: PlotAgent _apply_audit_loop 実装
- 対象ファイル: `src/agents/plot.py`
- 実装メソッド: `PlotAgent._apply_audit_loop()`
- 処理内容:
  1. `LogicalAuditor.audit_logical_consistency()` 调用
  2. `PlotIntegrityMonitor.check_integrity()` 调用
  3. 監査不通過時、最大3回のリトライ
  4. 最終失敗時 `RuntimeError` を送出

### ステップ28: PlotAgent _archive_and_save_plots 実装
- 対象ファイル: `src/agents/plot.py`
- 実装メソッド: `PlotAgent._archive_and_save_plots()`
- 処理内容:
  1. `async with self._uow_factory()` で UnitOfWork 生成
  2. `repo.archive_plots_from()` で古いプロットアーカイブ
  3. `repo.save_plot()` で新規プロット保存

### ステップ29: PlotAgent expand_plots 実装
- 対象ファイル: `src/agents/plot.py`
- 実装メソッド: `PlotAgent.expand_plots()`
- 処理内容:
  - `_plot_expander.expand_plots()` 委譲

### ステップ30: PlotAgent rebuild_hegemony_plot 実装
- 対象ファイル: `src/agents/plot.py`
- 実装メソッド: `PlotAgent.rebuild_hegemony_plot()`
- 処理内容:
  1. ブック取得とBible取得
  2. 過去文脈構築 (`_build_past_context`)
  3. 世界設定取得 (`_get_world_settings`)
  4. アークメタデータ生成
  5. 各話数ごとに `_expand_single_plot` + `_apply_audit_loop`
  6. `_archive_and_save_plots` でDB保存

### ステップ31: MarketingAgent 基本構造
- 作成ファイル: `src/agents/marketing.py`
- 実装クラス: `MarketingAgent`
- 初期化パラメータ:
  - `repo: Any`
  - `llm: Optional[LLMService]`
  - `prompt_manager: Any`

### ステップ32: MarketingAgent generate_pack 実装
- 対象ファイル: `src/agents/marketing.py`
- 実装メソッド: `MarketingAgent.generate_pack()`
- 処理内容:
  1. `prompt_manager.build_marketing_pack_prompt()` でプロンプト生成
  2. `llm.generate_json()` でマーケティング素材生成
  3. `metadata` を返回

### ステップ33: MarketingAgent create_export_package 実装
- 対象ファイル: `src/agents/marketing.py`
- 実装メソッド: `MarketingAgent.create_export_package()`
- 処理内容:
  1. `repo.get_book()` で作品情報取得
  2. `repo.get_all_non_anchor_chapters()` で全章取得
  3. `repo.get_all_characters()` で全キャラ取得
  4. `repo.get_latest_bible()` で世界設定取得
  5. `repo.get_all_plots()` で全プロット取得
  6. ZIP パッケージ化 (01_本文.txt, 02_設定集.txt, 03_プロット概要.txt, 04_データダンプ.json)
  7. `(bytes, filename)` を返回

### ステップ34: PlotExpander 基本構造
- 作成ファイル: `src/services/default_plot_expander.py`
- 実装クラス: `DefaultPlotExpander`
- 実装メソッド:
  - `expand_single_plot(...) -> PlotEpisode`
  - `expand_plots(...) -> List[PlotDetail]`

### ステップ35: StateValidator の実装
- 作成ファイル: `src/agents/state_validator.py`
- 実装クラス: `StateValidator`
- 実装メソッド:
  - `validate_transitions(prev_world_state, changes_obj) -> None`
- 例外:
  - `StateContradictionError` - 状態矛盾検出時

### ステップ36: PlotIntegrityMonitor の正式実装
- 対象ファイル: `src/agents/audit.py`
- 実装メソッド: `PlotIntegrityMonitor.check_integrity()`
- 処理内容:
  1. キーワード抽出
  2. ベクトル類似度計算
  3. しきい値判定
  4. `(is_ok, rate, failures)` を返回

---

## フェーズ4: Streamlit UI (ステップ37-48)

### ステップ37: UI Event Bus の実装
- 作成ファイル: `streamlit_app/event_bus.py`
- 実装クラス:
  - `UIEventType` - 列挙型
    - `REQUEST_GENERATE_PLAN`
    - `REQUEST_AUDIT_PLAN`
    - `REQUEST_GENERATE_EPISODE`
    - `REQUEST_CANCEL_JOB`
  - `UIEvent` - イベントデータクラス
  - `UIEventBus` - イベントバス
    - `subscribe(event_type, handler)`
    - `emit(event) -> Optional[Dict[str, Any]]`

### ステップ38: UI Store 基本クラス
- 作成ファイル: `streamlit_app/stores.py`
- 実装クラス:
  - `BaseStore` - 基底クラス (Streamlit キャッシュ利用)
  - `JobStore` - バックグラウンドジョブ状態管理
  - `PollStateStore` - ポーリング状態管理
  - `SessionStore` - セッション状態管理
  - `ToastStore` - トースト通知管理
  - `UIStateStore` - UI 状態統括

### ステップ39: UIControllerManager の実装
- 作成ファイル: `streamlit_app/controllers/manager.py`
- 実装クラス:
  - `SubController` - サブコントローラー基底
  - `UIControllerManager`
    - `__init__(engine)` - engine 注入 + バス登録
    - `emit(event_type, payload, stream_display) -> Optional[Dict[str, Any]]`

### ステップ40: Streamlit アダプター設定
- 作成ファイル: `config/streamlit_adapter.py`
- 実装クラス: `StreamlitConfig`
- 実装静的メソッド:
  - `get_session_state(key, default)` → `st.session_state[key]`
  - `set_session_state(key, value)` → `st.session_state[key] = value`
  - `cache_data(key, func)` → `st.cache_data(key)(func)`

### ステップ41: Streamlit メインアプリ設定
- 作成ファイル: `streamlit_app/main.py`
- 実装内容:
  - ページ構成 (Planning, Writing, Bible, Export)
  - サイドナビゲーション
  - テーマ設定

### ステップ42: Planning ページ実装
- 作成ファイル: `streamlit_app/pages/planning.py`
- 実装内容:
  - 作品作成フォーム
  - アーク設定UI
  - プロット生成ボタン + 進捗表示

### ステップ43: Writing ページ実装
- 作成ファイル: `streamlit_app/pages/writing.py`
- 実装内容:
  - エピソード一覧
  - 執筆ボタン + ストリーミング表示
  - 品質スコア表示

### ステップ44: Bible ページ実装
- 作成ファイル: `streamlit_app/pages/bible.py`
- 実装内容:
  - 世界設定エディタ
  - キャラクター管理
  - 制約条件設定

### ステップ45: Export ページ実装
- 作成ファイル: `streamlit_app/pages/export.py`
- 実装内容:
  - EPUB エクスポート
  - マーケティング素材生成
  - ZIP ダウンロード

### ステップ46: ストリーミング表示コンポーネント
- 作成ファイル: `streamlit_app/components/streaming.py`
- 実装関数:
  - `render_streaming_text(text_area, new_text)` - streaming 文本更新
  - `render_progress_bar(current, total, message)` - 進捗バー表示
  - `render_toast(message, level)` - トースト通知

### ステップ47: API クライアントモック (テスト用)
- 作成ファイル: `tests/ui/test_api_client_mock.py`
- 実装内容:
  - `MockAPIClient` - API 呼び出しモック
  - `mock_generate_plan()` - 計画生成モック
  - `mock_generate_episode()` - エピソード生成モック

### ステップ48: Streamlit 設定ファイル
- 作成ファイル: `streamlit_app/.streamlit/config.toml`
- 設定内容:
  - `[theme]` - カラーテーマ
  - `[server]` - サーバー設定

---

## フェーズ5: テスト基盤 (ステップ49-60)

### ステップ49: pytest 基本設定
- 対象ファイル: `autonovel/pytest.ini`
- 設定内容:
  ```ini
  [pytest]
  testpaths = autonovel/tests
  pythonpath = . autonovel autonovel/src
  addopts = -v --tb=short
  ```

### ステップ50: conftest.py 基本設定
- 対象ファイル: `autonovel/tests/conftest.py`
- 実装内容:
  - `AUTONOVEL_ROOT` パス設定
  - `sys.path.insert(0, str(AUTONOVEL_ROOT))`
  - 共通フィクスチャ定義

### ステップ51: LLM Fixtures
- 作成ファイル: `tests/fixtures/llm_verbose_fixture.py`
- 実装内容:
  - `verbose_edges.json` パス解決
  - `MockLLMService` フィクスチャ
  - `mock_generate_json()` スタブ

### ステップ52: ユニットテスト - モデル編
- 作成ファイル: `tests/unit/models/test_character.py`
- テストケース:
  - `test_character_registry_from_db()` - DB復元
  - `test_character_to_prompt()` - プロンプト生成
  - `test_character_relationship_validation()` - 関係性バリデーション

### ステップ53: ユニットテスト - リポジトリ編
- 作成ファイル: `tests/unit/repositories/test_book_repository.py`
- テストケース:
  - `test_create_book()` - 作品作成
  - `test_get_book()` - 作品取得
  - `test_update_book()` - 作品更新

### ステップ54: ユニットテスト - LLMサービス編
- 作成ファイル: `tests/unit/services/test_llm_service.py`
- テストケース:
  - `test_resolve_model()` - モデル解決
  - `test_generate_json_success()` - 正常系
  - `test_generate_json_timeout()` - タイムアウト系
  - `test_generate_text()` - テキスト生成

### ステップ55: ユニットテスト - 執筆サービス編
- 作成ファイル: `tests/unit/services/test_writing_services.py`
- テストケース:
  - `test_prepare_context()` - コンテキスト準備
  - `test_drafting_pass()` - ドラフティング
  - `test_audit_pass()` - 監査パス
  - `test_polishing_pass()` - 研磨パス

### ステップ56: 統合テスト - PlotAgent
- 作成ファイル: `tests/integration/agents/test_plot_agent.py`
- テストケース:
  - `test_expand_single_plot_success()` - 正常系
  - `test_expand_single_plot_with_retry()` - リトライ系
  - `test_rebuild_hegemony_plot()` - 再構築

### ステップ57: 統合テスト - MarketingAgent
- 作成ファイル: `tests/integration/agents/test_marketing_agent.py`
- テストケース:
  - `test_generate_pack()` - マーケティング素材生成
  - `test_create_export_package()` - エクスポート

### ステップ58: E2Eテスト - 作品作成から執筆まで
- 作成ファイル: `tests/e2e/test_full_workflow.py`
- テストケース:
  - `test_create_book_and_expand_plots()` - 計画作成
  - `test_generate_episodes()` - エピソード執筆
  - `test_export_package()` - パッケージ出力

### ステップ59: カバレッジ設定
- 対象ファイル: `pyproject.toml`
- 設定内容:
  ```toml
  [tool.coverage.run]
  source = ["src", "streamlit_app"]
  omit = ["tests/*", "*/__pycache__/*"]
  
  [tool.coverage.report]
  show_missing = true
  ```

### ステップ60: CI/CD設定ファイル
- 作成ファイル: `.github/workflows/ci.yml`
- 処理内容:
  - `on: [push, pull_request]`
  - ステップ: lint (ruff) → typecheck (mypy) → test (pytest) → coverage

---

## フェーズ6: 新機能実装 (ステップ61-72)

### ステップ61: メタプロンプトシステムのアーキテクチャ設計
- 作成ファイル: `src/core/meta_prompt_context.py`
- 実装クラス: `MetaPromptContext`
- フィールド:
  - `character_arcs: Dict[str, List[str]]` - キャラクター成長軌跡
  - `plot_timeline: List[Dict[str, Any]]` - プロットタイムライン
  - `theme_keywords: List[str]` - テーマキーワード
  - `narrative_constraints: List[str]` - 叙述制約

### ステップ62: メタプロンプト生成機能
- 作成ファイル: `src/core/meta_prompt_generator.py`
- 実装関数: `generate_meta_prompt(meta_context: MetaPromptContext) -> str`
- 処理内容:
  1. キャラクターARC矛盾チェック
  2. タイムライン整合性検証
  3. テーマキーワードの重み付け
  4. メタプロンプト文字列生成

### ステップ63: 文体サンプル登録API
- 対象ファイル: `src/backend/engine_style_rag.py`
- 追加メソッド:
  ```python
  async def add_style_fragment(tag: str, content: str, origin: str = "Masterpiece") -> bool:
      """文体サンプルをRAGに登録"""
      vec = await self._get_embedding(content)
      if vec:
          await self.repo.add_style_fragment(tag, content, vec, origin)
          return True
      return False
  ```

### ステップ64: 類似度検索最適化
- 対象ファイル: `src/backend/engine_style_rag.py`
- 改良内容:
  - `_embedding_cache` 容量上限設定 (max 1000 件)
  - LRU eviction ポリシー実装
  - `find_best_samples` 並列処理化

### ステップ65: ナラティブ指標保存機能
- 作成ファイル: `src/backend/database/repositories/narrative_metrics_repo.py`
- 実装クラス: `NarrativeMetricRepository`
- 実装メソッド:
  - `save_scene_metrics(book_id, branch_id, ep_num, scene_num, scores) -> None`
  - `get_metrics(book_id, ep_num) -> List[NarrativeMetricModel]`

### ステップ66: 品質スコアリング統合
- 対象ファイル: `src/services/writing_services.py` (拡張)
- 追加処理:
  1. `LogicalAuditor.score_narrative_metrics()` 调用
  2. `metrics_repo.save_scene_metrics()` 保存
  3. 没入スコア閾値チェック

### ステップ67: 遅延パッチ (Lazy Patch) 機能拡張
- 対象ファイル: `src/services/writing_services.py`
- 追加メソッド: `_register_lazy_patch()`
- 処理内容:
  1. `NarrativeConstraint` 生成
  2. `active_constraints` 追加
  3. `create_bible()` で新バージョン保存

### ステップ68: 外科的因果修復 (Surgical Healing)
- 対象ファイル: `src/services/writing_services.py`
- 実装メソッド: `surgical_causality_healing_pass()`
- 処理内容:
  1. 矛盾箇所特定
  2. ターゲットスニペット抽出
  3. `pm.build_surgical_causality_healing_prompt()` 生成
  4. LLM による修正生成
  5. 原文置換

### ステップ69: 作品データZIP EXPORT
- 対象ファイル: `src/agents/marketing.py` (拡張)
- 改良内容:
  - `create_export_package()` のエラー処理強化
  - キャラクター設定の完全包含
  - プロット概要の詳細化

### ステップ70: バックグラウンドタスク管理
- 作成ファイル: `src/backend/database/repositories/background_task_repo.py`
- 実装クラス: `BackgroundTaskRepository`
- 実装メソッド:
  - `create(task_id, total_steps) -> None`
  - `update_progress(task_id, current_step, message, sub_message, streaming_text) -> None`
  - `complete(task_id, result_data) -> None`
  - `fail(task_id, error) -> None`
  - `get_status(task_id) -> Optional[BackgroundTaskModel]`

### ステップ71: タスクの状態遷移管理
- 対象ファイル: `src/backend/database/repositories/background_task_repo.py`
- 追加機能:
  - 状態: `pending` → `running` → `completed` / `failed`
  - ログの逐次追加
  - エラー情報の保存

### ステップ72: 最終統合テストと品質確認
- 実行コマンド:
  ```bash
  python -m ruff check autonovel/src
  python -m mypy autonovel/src --strict
  python -m pytest autonovel/tests -v --tb=short
  python -m pytest autonovel/tests --collect-only
  ```
- 確認事項:
  - ruff: E722 エラー 0件
  - mypy: `--strict` モードでエラー 0件
  - pytest: 全テスト収集・実行成功
  - カバレッジ: 80%以上
```

## 5. 単体テスト要件（テストケース）

```python
# tests/unit/models/test_character.py

import pytest
from src.models.character import CharacterRegistry, CharacterRelationship, CharacterConcept

class TestCharacterRegistry:
    """CharacterRegistry モデルのユニットテスト"""
    
    def test_from_db_with_valid_json(self):
        """JSON文字列からの正しい復元"""
        data = '{"name": "剣豪", "role": "主人公", "personality": "寡黙", "ability": "剣術"}'
        char = CharacterRegistry.from_db(data)
        assert char.name == "剣豪"
        assert char.role == "主人公"
        assert char.personality == "寡黙"
        assert char.ability == "剣術"
    
    def test_from_db_with_invalid_json(self):
        """不正なJSONからの復元時、空オブジェクトを返"""
        data = "invalid json"
        char = CharacterRegistry.from_db(data)
        assert char.name == ""
        assert char.role == ""
    
    def test_from_db_with_empty_string(self):
        """空文字列からの復元時、空オブジェクトを返"""
        char = CharacterRegistry.from_db("")
        assert char.name == ""
    
    def test_to_prompt_basic(self):
        """基本的なプロンプト生成"""
        char = CharacterRegistry(
            name="剣豪",
            role="主人公",
            personality="寡黙",
            ability="剣術",
            tone="深い",
            iron_constraint="弱い者をめない",
            first_person="俺",
            second_person="お前",
            suffix_style="〜じゃ",
            expansion_hooks=["刀身が光る", "血の滴り"]
        )
        prompt = char.to_prompt()
        assert "Name: 剣豪 (主人公)" in prompt
        assert "Personality: 寡黙" in prompt
        assert "Ability: 剣術" in prompt
        assert "Tone: 深い" in prompt
        assert "IronConst: 弱い者をめない" in prompt
        assert "Pronouns: I=俺, You=お前" in prompt
        assert "Suffix: 〜じゃ" in prompt
        assert "ExpHooks: 刀身が光る, 血の滴り" in prompt
    
    def test_get_context_prompt_with_current_state(self):
        """現在状態を含むコンテキストプロンプト生成"""
        char = CharacterRegistry(
            name="剣豪",
            role="主人公",
            personality="寡黙",
            ability="剣術",
            tone="深い",
            relationships=[],
            dialogue_samples=["「覚悟せよ」"],
            expansion_hooks=["刀身が光る"]
        )
        prompt = char.get_context_prompt("闘争中")
        assert "■ 剣豪 (主人公)" in prompt
        assert "[CURRENT STATE: 闘争中]" in prompt
        assert "Tone: 深い" in prompt
        assert "Personality: 寡黙" in prompt
    
    def test_relationships_parsing(self):
        """関係性の正しいパース"""
        data = {
            "name": "主人公",
            "role": "主人公",
            "relationships": [
                {"target_char_name": "魔王", "type": "宿敵", "description": "千年前に戦った", "intensity": 5}
            ]
        }
        char = CharacterRegistry.model_validate(data)
        assert len(char.relationships) == 1
        assert char.relationships[0].target_char_name == "魔王"
        assert char.relationships[0].type == "宿敵"
        assert char.relationships[0].intensity == 5

class TestCharacterRelationship:
    """CharacterRelationship モデルのユニットテスト"""
    
    def test_valid_relationship(self):
        """有効な関係性の作成"""
        rel = CharacterRelationship(
            target_char_name="魔王",
            type="宿敵",
            description="千年前に戦った相手",
            intensity=5
        )
        assert rel.target_char_name == "魔王"
        assert rel.type == "宿敵"
        assert rel.intensity == 5
    
    def test_alias_resolve_target(self):
        """別名ターゲット解決 (target)"""
        rel = CharacterRelationship.model_validate({"target": "魔王", "relation": "宿敵"})
        assert rel.target_char_name == "魔王"
        assert rel.type == "宿敵"
    
    def test_alias_resolve_name(self):
        """別名ターゲット解決 (name)"""
        rel = CharacterRelationship.model_validate({"name": "魔王", "relationship": "宿敵"})
        assert rel.target_char_name == "魔王"
        assert rel.type == "宿敵"
    
    def test_alias_resolve_char(self):
        """別名ターゲット解決 (char)"""
        rel = CharacterRelationship.model_validate({"char": "魔王", "kind": "師弟"})
        assert rel.target_char_name == "魔王"
        assert rel.type == "師弟"
    
    def test_intensity_bounds(self):
        """強度のは0範囲境界値"""
        rel_min = CharacterRelationship(target_char_name="A", type="関係", intensity=1)
        rel_max = CharacterRelationship(target_char_name="A", type="関係", intensity=5)
        assert rel_min.intensity == 1
        assert rel_max.intensity == 5
    
    def test_optional_fields_default(self):
        """オプショナル字段のデフォルト値"""
        rel = CharacterRelationship(target_char_name="魔王", type="宿敵")
        assert rel.description == ""
        assert rel.intensity == 3
        assert rel.secret_aspect is None

class TestCharacterConcept:
    """CharacterConcept モデルのユニットテスト"""
    
    def test_valid_concept(self):
        """有効なコンセプトの作成"""
        concept = CharacterConcept(
            name="剣豪",
            trait="寡黙",
            core_idea="孤独な最强",
            appeal_point="カタルシス"
        )
        assert concept.name == "剣豪"
        assert concept.trait == "寡黙"
        assert concept.core_idea == "孤独な最强"
        assert concept.appeal_point == "カタルシス"
    
    def test_villain_concept_optional(self):
        """敵対者概念は任意"""
        concept = CharacterConcept(
            name="剣豪",
            trait="寡黙",
            core_idea="孤独な最强",
            appeal_point="カタルシス"
        )
        assert concept.villain_concept is None

# tests/unit/services/test_llm_service.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.llm_service import LLMService

class TestLLMService:
    """LLMService のユニットテスト"""
    
    def test_resolve_model_writing(self):
        """writing 目的のモデル解決"""
        service = LLMService(api_key="test_key")
        model = service._resolve_model("writing")
        assert model == "gemini-2.0-flash"
    
    def test_resolve_model_audit(self):
        """audit 目的のモデル解決"""
        service = LLMService(api_key="test_key")
        model = service._resolve_model("audit")
        assert model == "gemini-2.0-flash"
    
    def test_resolve_model_marketing(self):
        """marketing 目的のモデル解決"""
        service = LLMService(api_key="test_key")
        model = service._resolve_model("marketing")
        assert model == "gemini-2.0-flash"
    
    def test_resolve_model_unknown(self):
        """未知のpurposeでデフォルト解決"""
        service = LLMService(api_key="test_key")
        model = service._resolve_model("unknown_purpose")
        # デフォルトで general モデルが返る (実装依存)
        assert model is not None
    
    @pytest.mark.asyncio
    async def test_generate_json_success(self):
        """generate_json 成功ケース"""
        service = LLMService(api_key="test_key")
        mock_response = {"metadata": {"title": "テスト"}, "story_content": "本文"}
        
        with patch.object(service, '_ensure_factory') as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate_json = AsyncMock(return_value=(mock_response["metadata"], mock_response["story_content"], {}))
            mock_factory.return_value.get_client.return_value = mock_client
            
            result = await service.generate_json(
                purpose="writing",
                prompt="テストプロンプト",
                response_schema=None
            )
            
            assert result["success"] is True
            assert result["metadata"] == mock_response["metadata"]
            assert result["story_content"] == mock_response["story_content"]
    
    @pytest.mark.asyncio
    async def test_generate_json_with_schema(self):
        """generate_json with response_schema"""
        service = LLMService(api_key="test_key")
        
        with patch.object(service, '_ensure_factory') as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate_json = AsyncMock(return_value=({"result": "ok"}, "text", {}))
            mock_factory.return_value.get_client.return_value = mock_client
            
            class DummySchema:
                pass
            
            result = await service.generate_json(
                purpose="writing",
                prompt="テスト",
                response_schema=DummySchema
            )
            
            assert result["success"] is True
            mock_client.generate_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """generate_text 成功ケース"""
        service = LLMService(api_key="test_key")
        
        with patch.object(service, '_ensure_factory') as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate_text = AsyncMock(return_value=("生成されたテキスト", {}))
            mock_factory.return_value.get_client.return_value = mock_client
            
            result = await service.generate_text(
                purpose="writing",
                prompt="テストプロンプト"
            )
            
            assert result == "生成されたテキスト"
    
    @pytest.mark.asyncio
    async def test_generate_json_api_error(self):
        """generate_json API エラーケース"""
        service = LLMService(api_key="test_key")
        
        with patch.object(service, '_ensure_factory') as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate_json = AsyncMock(side_effect=Exception("API Error"))
            mock_factory.return_value.get_client.return_value = mock_client
            
            # 例外が上位に伝わる
            with pytest.raises(Exception):
                await service.generate_json(
                    purpose="writing",
                    prompt="テスト"
                )

# tests/unit/services/test_writing_services.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.writing_services import WritingGenerationContext, GenerationLoopManager

class TestWritingGenerationContext:
    """WritingGenerationContext のユニットテスト"""
    
    def test_build_sys_inst_basic(self):
        """システム命令の基本構築"""
        ctx = WritingGenerationContext(
            sys_inst="あなたは小説家です",
            pov_instruction="一人称で書け",
            feedback_patch=""
        )
        result = ctx.build_sys_inst()
        assert "あなたは小説家です" in result
        assert "一人称で書け" in result
    
    def test_build_sys_inst_with_feedback(self):
        """フィードバックパッチ含むシステム命令構築"""
        ctx = WritingGenerationContext(
            sys_inst="あなたは小説家です",
            pov_instruction="",
            feedback_patch="もっと具体的に書け"
        )
        result = ctx.build_sys_inst()
        assert "あなたは小説家です" in result
        assert "もっと具体的に書け" in result
    
    def test_build_sys_inst_empty_pov(self):
        """poin_instruction 空の場合"""
        ctx = WritingGenerationContext(
            sys_inst="あなたは小説家です",
            pov_instruction="",
            feedback_patch=""
        )
        result = ctx.build_sys_inst()
        assert result == "あなたは小説家です"
    
    def test_build_fw_prompt_basic(self):
        """fw_promptの基本構築"""
        ctx = WritingGenerationContext(
            fw_prompt="物語を書け",
            pov_instruction="三人称で書け",
            expanded_beats="",
            feedback_patch=""
        )
        result = ctx.build_fw_prompt()
        assert "物語を書け" in result
        assert "三人称で書け" in result
    
    def test_build_fw_prompt_with_beats(self):
        """ビート分解を含むfw_prompt構築"""
        ctx = WritingGenerationContext(
            fw_prompt="物語を書け",
            pov_instruction="",
            expanded_beats="ビート1: 主人公が歩く\nビート2: 敵が現れる",
            feedback_patch=""
        )
        result = ctx.build_fw_prompt()
        assert "物語を書け" in result
        assert "ビート1: 主人公が歩く" in result
        assert "ビート2: 敵が現れる" in result
    
    def test_build_fw_prompt_with_suffix(self):
        """suffix 付きfw_prompt構築"""
        ctx = WritingGenerationContext(
            fw_prompt="物語を書け",
            pov_instruction="",
            expanded_beats="",
            feedback_patch=""
        )
        result = ctx.build_fw_prompt(suffix="【追加指示】")
        assert "物語を書け" in result
        assert "【追加指示】" in result
    
    def test_model_default_values(self):
        """モデルのデフォルト値"""
        ctx = WritingGenerationContext()
        assert ctx.sys_inst == ""
        assert ctx.fw_prompt == ""
        assert ctx.pov_instruction == ""
        assert ctx.expanded_beats == ""
        assert ctx.feedback_patch == ""
        assert ctx.style_key == "style_web_standard"
        assert ctx.target_word_count == 2000
        assert ctx.enable_polishing is True
        assert ctx.prose_sample == ""

# tests/unit/repositories/test_plot_repository.py

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.plot import PlotRepository
from src.backend.database.models import Plot

class TestPlotRepository:
    """PlotRepository のユニットテスト"""
    
    @pytest.mark.asyncio
    async def test_save_new_plot(self):
        """新規プロット保存"""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        
        repo = PlotRepository(mock_session)
        
        plot_data = {
            "ep_num": 1,
            "title": "第1話",
            "detailed_blueprint": "開始地点",
            "tension": 50,
            "catharsis": 0,
            "is_catharsis": False
        }
        
        result = await repo.save(branch_id=1, ep_num=1, plot_data=plot_data)
        
        assert result is True
        mock_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_episode_found(self):
        """話数によるプロット取得（存在する場合）"""
        mock_session = AsyncMock()
        
        mock_plot = MagicMock()
        mock_plot.book_id = 1
        mock_plot.branch_id = 1
        mock_plot.ep_num = 1
        mock_plot.title = "第1話"
        mock_plot.detailed_blueprint = "開始地点"
        mock_plot.tension = 50
        mock_plot.to_dict.return_value = {
            "book_id": 1,
            "branch_id": 1,
            "ep_num": 1,
            "title": "第1話",
            "detailed_blueprint": "開始地点",
            "tension": 50
        }
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plot
        mock_session.execute.return_value = mock_result
        
        repo = PlotRepository(mock_session)
        result = await repo.get_by_episode(book_id=1, branch_id=1, ep_num=1)
        
        assert result is not None
        assert result["ep_num"] == 1
        assert result["title"] == "第1話"
    
    @pytest.mark.asyncio
    async def test_get_by_episode_not_found(self):
        """話数によるプロット取得（存在しない場合）"""
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = PlotRepository(mock_session)
        result = await repo.get_by_episode(book_id=1, branch_id=1, ep_num=999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_range(self):
        """範囲指定によるプロット一覧取得"""
        mock_session = AsyncMock()
        
        mock_plot1 = MagicMock()
        mock_plot1.to_dict.return_value = {"ep_num": 1, "title": "第1話"}
        mock_plot2 = MagicMock()
        mock_plot2.to_dict.return_value = {"ep_num": 2, "title": "第2話"}
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_plot1, mock_plot2]
        mock_session.execute.return_value = mock_result
        
        repo = PlotRepository(mock_session)
        results = await repo.get_range(book_id=1, branch_id=1, start_ep=1, end_ep=3)
        
        assert len(results) == 2
        assert results[0]["ep_num"] == 1
        assert results[1]["ep_num"] == 2
    
    @pytest.mark.asyncio
    async def test_get_range_empty(self):
        """範囲指定で結果なし"""
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        repo = PlotRepository(mock_session)
        results = await repo.get_range(book_id=1, branch_id=1, start_ep=100, end_ep=200)
        
        assert len(results) == 0

# tests/integration/agents/test_plot_agent.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.plot import PlotAgent

class TestPlotAgent:
    """PlotAgent の統合テスト"""
    
    @pytest.mark.asyncio
    async def test_expand_single_plot_success(self):
        """正常系: 単一プロット展開"""
        mock_repo = MagicMock()
        mock_pm = MagicMock()
        mock_generate_json = AsyncMock()
        
        mock_plot_data = {
            "core_info": {
                "ep_num": 1,
                "title": "第1話",
                "one_line_summary": "始まり",
                "detailed_blueprint": "物語はここに始まる"
            },
            "analytics": {
                "tension": 50,
                "catharsis": 0,
                "is_catharsis": False
            }
        }
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metadata = mock_plot_data
        mock_generate_json.return_value = mock_result
        
        mock_expander = MagicMock()
        mock_expander.expand_single_plot = AsyncMock(return_value=None)
        
        agent = PlotAgent(
            repo=mock_repo,
            pm=mock_pm,
            generate_json=mock_generate_json,
            plot_expander=mock_expander
        )
        
        result = await agent._expand_single_plot(
            book_title="テスト小説",
            ep_num=1,
            arc_metadata={},
            past_context="",
            world_settings="{}",
            reporter=None
        )
        
        # expand_single_plotが失敗したので、generate_jsonが呼ばれる
        mock_generate_json.assert_called_once()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_expand_single_plot_uses_expander_first(self):
        """プロットエクスパンダーが優先して呼ばれる"""
        mock_repo = MagicMock()
        mock_pm = MagicMock()
        mock_generate_json = AsyncMock()
        
        mock_expander = MagicMock()
        mock_expander.expand_single_plot = AsyncMock(return_value=MagicMock(
            core_info=MagicMock(ep_num=1),
            analytics=MagicMock(tension=50)
        ))
        
        agent = PlotAgent(
            repo=mock_repo,
            pm=mock_pm,
            generate_json=mock_generate_json,
            plot_expander=mock_expander
        )
        
        result = await agent._expand_single_plot(
            book_title="テスト小説",
            ep_num=1,
            arc_metadata={},
            past_context="",
            world_settings="{}",
            reporter=None
        )
        
        mock_expander.expand_single_plot.assert_called_once()
        # generate_jsonは呼ばれない
        mock_generate_json.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_build_past_context(self):
        """過去文脈の構築"""
        mock_repo = MagicMock()
        mock_pm = MagicMock()
        
        mock_plot1 = MagicMock()
        mock_plot1.ep_num = 1
        mock_plot1.one_line_summary = "開始"
        mock_plot2 = MagicMock()
        mock_plot2.ep_num = 2
        mock_plot2.one_line_summary = "展開"
        
        mock_repo.get_plots_between = AsyncMock(return_value=[mock_plot1, mock_plot2])
        
        agent = PlotAgent(
            repo=mock_repo,
            pm=mock_pm,
            generate_json=AsyncMock()
        )
        
        result = await agent._build_past_context(branch_id=1, start_ep=3)
        
        assert "第1話: 開始" in result
        assert "第2話: 展開" in result
    
    @pytest.mark.asyncio
    async def test_build_past_context_empty(self):
        """過去文脈が空の場合"""
        mock_repo = MagicMock()
        mock_repo.get_plots_between = AsyncMock(return_value=[])
        
        agent = PlotAgent(
            repo=mock_repo,
            pm=MagicMock(),
            generate_json=AsyncMock()
        )
        
        result = await agent._build_past_context(branch_id=1, start_ep=1)
        
        assert "過去のプロットはありません" in result

# tests/integration/agents/test_marketing_agent.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import io
import zipfile
from src.agents.marketing import MarketingAgent

class TestMarketingAgent:
    """MarketingAgent の統合テスト"""
    
    @pytest.mark.asyncio
    async def test_generate_pack_success(self):
        """マーケティング素材生成成功"""
        mock_llm = AsyncMock()
        mock_llm.generate_json.return_value = {
            "success": True,
            "metadata": {
                "catchphrase": "テストキャッチコピー",
                "tags": ["ファンタジー", "戦闘"],
                "ab_test_candidates": []
            }
        }
        
        mock_pm = MagicMock()
        mock_pm.build_marketing_pack_prompt.return_value = "プロンプト"
        
        agent = MarketingAgent(
            repo=MagicMock(),
            llm=mock_llm,
            prompt_manager=mock_pm
        )
        
        result = await agent.generate_pack(
            book_title="テスト小説",
            synopsis="テストあらすじ",
            latest_ep=10
        )
        
        assert result["catchphrase"] == "テストキャッチコピー"
        assert "ファンタジー" in result["tags"]
    
    @pytest.mark.asyncio
    async def test_generate_pack_without_prompt_manager(self):
        """プロンプトマネージャーなしの場合"""
        agent = MarketingAgent(
            repo=MagicMock(),
            llm=MagicMock(),
            prompt_manager=None
        )
        
        with pytest.raises(ValueError, match="PromptManager is required"):
            await agent.generate_pack(
                book_title="テスト",
                synopsis="テスト",
                latest_ep=1
            )
    
    @pytest.mark.asyncio
    async def test_create_export_package_success(self):
        """ZIPエクスポート成功"""
        mock_book = MagicMock()
        mock_book.id = 1
        mock_book.title = "テスト小説"
        mock_book.current_branch_id = 1
        
        mock_repo = MagicMock()
        mock_repo.get_book = AsyncMock(return_value=mock_book)
        mock_repo.get_all_non_anchor_chapters = AsyncMock(return_value=[
            MagicMock(ep_num=1, title="第1話", content="本文1"),
            MagicMock(ep_num=2, title="第2話", content="本文2")
        ])
        mock_repo.get_all_characters = AsyncMock(return_value=[
            MagicMock(name="主人公", role="主人公", registry_data="{}")
        ])
        mock_repo.get_latest_bible = AsyncMock(return_value=MagicMock(
            settings={"world": "設定"}
        ))
        mock_repo.get_all_plots = AsyncMock(return_value=[
            MagicMock(ep_num=1, title="第1話", one_line_summary="開始"),
            MagicMock(ep_num=2, title="第2話", one_line_summary="展開")
        ])
        
        mock_llm = MagicMock()
        mock_pm = MagicMock()
        
        agent = MarketingAgent(
            repo=mock_repo,
            llm=mock_llm,
            prompt_manager=mock_pm
        )
        
        zip_data, filename = await agent.create_export_package(book_id=1)
        
        assert isinstance(zip_data, bytes)
        assert filename == "export_1.zip"
        
        # ZIP 内容を確認
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as z:
            names = z.namelist()
            assert "01_本文.txt" in names
            assert "02_キャラクター・世界観設定集.txt" in names
            assert "03_プロット概要.txt" in names
            assert "04_データダンプ.json" in names
    
    @pytest.mark.asyncio
    async def test_create_export_package_book_not_found(self):
        """作品が見つからない場合"""
        mock_repo = MagicMock()
        mock_repo.get_book = AsyncMock(return_value=None)
        
        agent = MarketingAgent(
            repo=mock_repo,
            llm=MagicMock(),
            prompt_manager=MagicMock()
        )
        
        with pytest.raises(ValueError, match="作品が見つかりません"):
            await agent.create_export_package(book_id=999)

# tests/e2e/test_full_workflow.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.plot import PlotAgent
from src.agents.marketing import MarketingAgent
import io
import zipfile

class TestFullWorkflow:
    """完全ワークフローのE2Eテスト"""
    
    @pytest.mark.asyncio
    async def test_create_book_to_export(self):
        """作品作成からエクスポートまで"""
        # 1. ブック作成
        mock_book_repo = MagicMock()
        mock_book_repo.create.return_value = 1
        mock_book_repo.get_by_id.return_value = MagicMock(
            id=1,
            title="テスト小説",
            current_branch_id=1
        )
        
        # 2. キャラクター作成
        mock_char_repo = MagicMock()
        mock_char_repo.create.return_value = 1
        
        # 3. Bible作成
        mock_bible_repo = MagicMock()
        
        # 4. マーケティング生成
        mock_llm = AsyncMock()
        mock_llm.generate_json.return_value = {
            "success": True,
            "metadata": {
                "catchphrase": "テストキャッチコピー",
                "tags": ["ファンタジー", "戦闘"],
                "ab_test_candidates": []
            }
        }
        
        mock_pm = MagicMock()
        mock_pm.build_marketing_pack_prompt.return_value = "マーケティングプロンプト"
        
        marketing_agent = MarketingAgent(
            repo=MagicMock(
                get_book=AsyncMock(return_value=MagicMock(
                    id=1,
                    title="テスト小説",
                    current_branch_id=1
                )),
                get_all_non_anchor_chapters=AsyncMock(return_value=[]),
                get_all_characters=AsyncMock(return_value=[]),
                get_latest_bible=AsyncMock(return_value=None),
                get_all_plots=AsyncMock(return_value=[])
            ),
            llm=mock_llm,
            prompt_manager=mock_pm
        )
        
        result = await marketing_agent.create_export_package(book_id=1)
        
        assert result is not None
        zip_data, filename = result
        assert isinstance(zip_data, bytes)
        assert filename == "export_1.zip"
    
    @pytest.mark.asyncio
    async def test_plot_generation_workflow(self):
        """プロット生成から保存まで"""
        mock_repo = MagicMock()
        mock_repo.get_book.return_value = MagicMock(id=1, title="テスト", current_branch_id=1)
        mock_repo.get_latest_bible.return_value = MagicMock(
            settings={"world": "設定"}
        )
        mock_repo.get_plots_between.return_value = []
        
        mock_pm = MagicMock()
        mock_generate_json = AsyncMock()
        mock_generate_json.return_value = MagicMock(
            success=True,
            metadata={
                "core_info": {
                    "ep_num": 1,
                    "title": "第1話",
                    "one_line_summary": "始まり",
                    "detailed_blueprint": "開始"
                },
                "analytics": {
                    "tension": 50,
                    "catharsis": 0,
                    "is_catharsis": False
                }
            }
        )
        
        mock_uow = AsyncMock()
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)
        mock_uow.plots = MagicMock()
        
        mock_uow_factory = MagicMock(return_value=mock_uow)
        
        agent = PlotAgent(
            repo=mock_repo,
            pm=mock_pm,
            generate_json=mock_generate_json,
            plot_expander=None,
            uow_factory=mock_uow_factory
        )
        
        result = await agent._build_past_context(branch_id=1, start_ep=1)
        
        assert "過去のプロットはありません" in result

# tests/unit/models/test_plot.py

import pytest
from src.models.plot import PlotEpisode, PlotAnalytics, PlotCoreInfo, SceneBeat, MasterSceneBlock

class TestPlotModels:
    """プロット関連モデルのユニットテスト"""
    
    def test_plot_episode_creation(self):
        """PlotEpisode の作成"""
        episode = PlotEpisode(
            core_info=PlotCoreInfo(
                ep_num=1,
                title="第1話",
                one_line_summary="始まり",
                detailed_blueprint="開始地点"
            ),
            analytics=PlotAnalytics(
                tension=50,
                catharsis=0,
                is_catharsis=False
            )
        )
        
        assert episode.ep_num == 1
        assert episode.title == "第1話"
        assert episode.tension == 50
        assert episode.is_catharsis is False
    
    def test_plot_episode_properties(self):
        """PlotEpisode のプロパティアクセス"""
        episode = PlotEpisode(
            core_info=PlotCoreInfo(
                ep_num=1,
                title="第1話",
                detailed_blueprint="開始"
            ),
            analytics=PlotAnalytics(tension=50)
        )
        
        # プロパティ 통한アクセス
        assert episode.ep_num == 1
        assert episode.title == "第1話"
        assert episode.detailed_blueprint == "開始"
        assert episode.tension == 50
    
    def test_plot_analytics_defaults(self):
        """PlotAnalytics のデフォルト値"""
        analytics = PlotAnalytics()
        
        assert analytics.tension == 50
        assert analytics.tension_delta == 0
        assert analytics.catharsis == 0
        assert analytics.is_catharsis is False
        assert analytics.love_meter == 0
        assert analytics.catharsis_type == "なし"
    
    def test_scene_beat_creation(self):
        """SceneBeat の作成"""
        beat = SceneBeat(
            beat_num=1,
            physical_action="主人公が剣を抜く",
            sensory_tags=["視覚", "触覚"],
            emotion_phase="buildup",
            word_budget=200
        )
        
        assert beat.beat_num == 1
        assert beat.physical_action == "主人公が剣を抜く"
        assert "視覚" in beat.sensory_tags
        assert beat.word_budget == 200
    
    def test_master_scene_block_creation(self):
        """MasterSceneBlock の作成"""
        scene = MasterSceneBlock(
            scene_number=1,
            action="戦闘シーン",
            dialogue_point="決め台詞",
            beats=[
                SceneBeat(beat_num=1, physical_action="剣を振る")
            ]
        )
        
        assert scene.scene_number == 1
        assert scene.action == "戦闘シーン"
        assert len(scene.beats) == 1
    
    def test_plot_episode_with_extra_engines(self):
        """PlotEpisode の extra_engines"""
        episode = PlotEpisode(
            core_info=PlotCoreInfo(ep_num=1, title="テスト"),
            analytics=PlotAnalytics(),
            extra_engines={"custom_field": "value"}
        )
        
        assert episode.extra_engines["custom_field"] == "value"

# tests/unit/models/test_audit.py

import pytest
from src.models.audit import AuditIssue, LogicalAuditIssueList, CriticFeedback, ImmersionScore

class TestAuditModels:
    """監査関連モデルのユニットテスト"""
    
    def test_audit_issue_creation(self):
        """AuditIssue の作成"""
        issue = AuditIssue(
            category="生死",
            severity="Critical",
            description="キャラクターが死亡后又生存している",
            evidence_past="第5話で死亡",
            evidence_current="第8話で生存",
            constraint_for_next_ep="以降の執筆では死亡設定を統一する"
        )
        
        assert issue.category == "生死"
        assert issue.severity == "Critical"
        assert "死亡后又生存" in issue.description
    
    def test_logical_audit_issue_list_empty(self):
        """空の監査結果"""
        issue_list = LogicalAuditIssueList(is_consistent=True, issues=[])
        
        assert issue_list.is_consistent is True
        assert len(issue_list.issues) == 0
        assert issue_list.overall_severity == "None"
    
    def test_logical_audit_issue_list_with_issues(self):
        """矛盾ありの監査結果"""
        issue_list = LogicalAuditIssueList(
            is_consistent=False,
            issues=[
                AuditIssue(
                    category="生死",
                    severity="Critical",
                    description="矛盾1"
                ),
                AuditIssue(
                    category="場所",
                    severity="Minor",
                    description="矛盾2"
                )
            ]
        )
        
        assert issue_list.is_consistent is False
        assert len(issue_list.issues) == 2
        assert issue_list.overall_severity == "Critical"
    
    def test_critic_feedback_creation(self):
        """CriticFeedback の作成"""
        feedback = CriticFeedback(
            has_critical_issues=True,
            overall_assessment="2件の重大な矛盾",
            directives=[],
            rewrite_guidance="修正意見を記載"
        )
        
        assert feedback.has_critical_issues is True
        assert "重大な矛盾" in feedback.overall_assessment
    
    def test_immersion_score_calculation(self):
        """没入スコア計算"""
        score = ImmersionScore(
            pov_stability=0.8,
            empathy_gap=0.2,
            curiosity_hook_rate=0.9,
            sensory_density=0.7
        )
        
        total = score.calculate_total()
        
        assert total > 0
        assert score.is_immersive is (total >= 50.0)
    
    def test_immersion_score_from_dict(self):
        """辞書からの復元"""
        data = {
            "pov_stability": 0.8,
            "empathy_gap": 0.3,
            "curiosity_hook_rate": 0.7,
            "sensory_density": 0.6
        }
        
        score = ImmersionScore.from_dict(data)
        
        assert score.pov_stability == 0.8
        assert score.empathy_gap == 0.3
```

---

**実装時の注意事項:**
1. 各ステップは独立して実行可能
2. ステップ間の依存関係は明記済み
3. 具体的ファイル名・関数名・処理ロジックを省略なく記載
4. 低性能LLMでも機械的に実装可能な詳細レベル
5. テストケースは正常系と異常系の両方を包含