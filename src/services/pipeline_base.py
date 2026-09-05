"""
パイプライン共通基底クラス
循環インポート回避のため分離
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from pydantic import BaseModel, Field

from src.models.foreshadowing import Foreshadowing
from src.models.hook import Hook
from src.models.illustration_point import IllustrationPoint

if TYPE_CHECKING:
    from src.backend.background import StatusReporter
    from src.backend.engine import UltimateHegemonyEngine


class WorkflowContext(BaseModel):
    # === 基本設定 (FullAuto 由来) ===
    genre: str
    keywords: str
    archetype_key: str
    target_eps: int
    initial_limit: int
    word_count: int
    concept: str = ""
    tone_vibe: float = 0.6
    user_prompt: str = ""

    # === 実行状態 ===
    book_id: int | None = None
    chars_count: int = 0
    failed_episodes: list[dict[str, Any]] = Field(default_factory=list)
    zip_data: bytes | None = None
    zip_filename: str | None = None
    title: str = ""
    easy_parameters: dict[str, Any] = Field(default_factory=dict)

    # === EasyMode 由来設定 (SpiceGuard・監査リライト) ===
    enable_spice_guard: bool = True
    max_rewrite_iterations: int = 3
    target_audit_score: float = 95.0

    # === FullAuto 由来設定 (挿絵・カタルシス等) ===
    # 挿絵生成が無効 (`enable_illustration=False`) 場合でも ``illustration_settings`` は
    # 空 dict のままで OK。``enableIllustration`` キーがある時のみ Step 内で実処理する。
    enable_illustration: bool = False
    illustration_settings: dict[str, Any] = Field(default_factory=dict)
    enable_catharsis_analysis: bool = True

    # === 共通オプション ===
    enable_marketing: bool = True
    max_retries: int = 1
    is_easy_mode: bool = False

    # === 内部用 (Step間受け渡し) ===
    preset_name: str = ""
    spice_elements: list = Field(default_factory=list)
    catharsis_pattern: dict[str, Any] = Field(default_factory=dict)
    catharsis_positions: list = Field(default_factory=list)
    average_audit_score: float = 0.0
    episodes_detail: list[dict[str, Any]] = Field(default_factory=list)
    foreshadowings: List[Foreshadowing] = Field(default_factory=list)
    current_volume: int = 1
    current_episode: int = 0
    hooks: List[Hook] = Field(default_factory=list)
    hook_generation_index: int = 0
    illustration_points: List[IllustrationPoint] = Field(default_factory=list)

    # === Skip/警告の観測用 ===
    # 各 Step がスキップした理由 (例: "illustration: book_id is None") を積む。
    # テスト・運用監視から「silent skip」を検知できるようにする。
    warnings: list[str] = Field(default_factory=list)

    # === 拡張出力 (Step が書き込む) ===
    illustrations: list[dict[str, Any]] = Field(default_factory=list)
    marketing_pack: dict[str, Any] = Field(default_factory=list)


class WorkflowStep:
    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        """Execute step. Returns True to continue, False to halt/break."""
        raise NotImplementedError()