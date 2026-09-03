"""
統合パイプライン設定モデル
FullAutoWorkflow と EasyModePipeline の設定を統合
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnifiedPipelineConfig:
    """全自動・かんたんモード共通のパイプライン設定"""

    # === 基本設定 (両モード共通) ===
    genre: str = "ファンタジー"
    keywords: str = ""
    archetype_key: str = "王道ざまぁ（爽快感最大）"
    target_eps: int = 10
    initial_limit: int = 3
    word_count: int = 2000
    concept: str = ""
    tone_vibe: float = 0.6
    user_prompt: str = ""

    # === EasyMode 由来設定 (SpiceGuard・監査リライト) ===
    enable_spice_guard: bool = True
    max_rewrite_iterations: int = 3
    target_audit_score: float = 95.0

    # === FullAuto 由来設定 (挿絵・カタルシス等) ===
    enable_illustration: bool = False
    illustration_settings: dict[str, Any] = field(default_factory=dict)
    enable_catharsis_analysis: bool = True

    # === 共通オプション ===
    enable_marketing: bool = True
    max_retries: int = 1
    is_easy_mode: bool = False

    # === 進捗コールバック (互換性維持用) ===
    progress_callback: Callable[[str, int, int], None] | None = None

    # === 内部用 (Step間受け渡し) ===
    preset_name: str = ""
    spice_elements: list = field(default_factory=list)
    catharsis_pattern: dict[str, Any] = field(default_factory=dict)
    catharsis_positions: list = field(default_factory=list)

    def to_workflow_context(self) -> WorkflowContext:
        """WorkflowContext へ変換 (遅延インポートで循環回避)"""
        from src.services.auto_workflow_pipeline import WorkflowContext

        return WorkflowContext(
            genre=self.genre,
            keywords=self.keywords,
            archetype_key=self.archetype_key,
            target_eps=self.target_eps,
            initial_limit=self.initial_limit,
            word_count=self.word_count,
            concept=self.concept,
            tone_vibe=self.tone_vibe,
            user_prompt=self.user_prompt,
            enable_spice_guard=self.enable_spice_guard,
            max_rewrite_iterations=self.max_rewrite_iterations,
            target_audit_score=self.target_audit_score,
            enable_illustration=self.enable_illustration,
            illustration_settings=self.illustration_settings,
            enable_catharsis_analysis=self.enable_catharsis_analysis,
            enable_marketing=self.enable_marketing,
            max_retries=self.max_retries,
            is_easy_mode=self.is_easy_mode,
            preset_name=self.preset_name,
        )

    @classmethod
    def from_full_auto_kwargs(cls, **kwargs) -> UnifiedPipelineConfig:
        """FullAutoWorkflow の kwargs から生成"""
        return cls(
            genre=kwargs.get("genre", "ファンタジー"),
            keywords=kwargs.get("keywords", ""),
            archetype_key=kwargs.get("archetype_key", "王道ざまぁ（爽快感最大）"),
            target_eps=kwargs.get("target_eps", 10),
            initial_limit=kwargs.get("initial_limit", 3),
            word_count=kwargs.get("word_count", 2000),
            concept=kwargs.get("concept", ""),
            tone_vibe=kwargs.get("tone_vibe", 0.6),
            user_prompt=kwargs.get("user_prompt", ""),
            enable_illustration=bool(kwargs.get("illustration_settings", {}).get("enableIllustration", False)),
            illustration_settings=kwargs.get("illustration_settings", {}),
            enable_spice_guard=kwargs.get("enable_spice_guard", False),
            is_easy_mode=False,
        )

    @classmethod
    def from_easy_mode_kwargs(cls, **kwargs) -> UnifiedPipelineConfig:
        """EasyModeWorkflow の kwargs から生成"""
        genre = kwargs.get("genre", "ファンタジー")
        # ジャンルからプリセット名を推定
        preset_map = {
            "ファンタジー": "zarma",
            "恋愛": "aku_reijo",
            "SF": "cheat_tensei",
            "歴史": "slow_life",
            "官能/ロマンス": "pure_love_erotic",
        }
        return cls(
            genre=genre,
            keywords=", ".join(kwargs.get("keywords", [])) if isinstance(kwargs.get("keywords"), list) else kwargs.get("keywords", ""),
            archetype_key=kwargs.get("protagonist_type", "チート主人公"),
            target_eps=kwargs.get("target_episodes", 10),
            word_count=kwargs.get("words_per_episode", 2000),
            enable_spice_guard=kwargs.get("enable_audit", True),
            max_rewrite_iterations=kwargs.get("max_rewrites", 2),
            target_audit_score=95.0,
            is_easy_mode=True,
            preset_name=preset_map.get(genre, "zarma"),
            progress_callback=kwargs.get("progress_callback"),
        )


# 遅延インポート用の前方宣言
class WorkflowContext:
    pass
