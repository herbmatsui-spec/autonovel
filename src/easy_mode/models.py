"""
共通データクラス・設定クラス
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SpiceElement:
    """尖り要素"""

    type: str  # "unique_metaphor", "character_voice", "plot_twist_marker", "emotional_raw", "rule_break_for_effect"
    text: str  # 元のテキスト
    position: int  # 文字位置
    priority: str  # "critical", "high", "medium", "low"
    metadata: Dict = field(default_factory=dict)


@dataclass
class EpisodeResult:
    """1話分の生成結果"""

    episode_num: int
    title: str
    content: str
    word_count: int
    audit_score: float
    audit_passed: bool
    rewrite_count: int
    spice_elements: List[SpiceElement]
    metadata: Dict[str, Any]
    needs_human_review: bool = False


@dataclass
class SeriesResult:
    """シリーズ全体の生成結果"""

    genre: str
    title: str
    concept: str
    total_episodes: int
    episodes: List[EpisodeResult]
    bible: Dict[str, Any]
    plot_outline: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "completed"  # "in_progress", "completed", "failed", "paused"


@dataclass
class PipelineConfig:
    """パイプライン設定"""

    genre: str
    target_episodes: int = 8
    max_rewrite_iterations: int = 3
    target_audit_score: float = 95.0
    enable_spice_guard: bool = True
    progress_callback: Optional[Callable[[str, int, int], None]] = None


@dataclass
class RetryConfig:
    """LLMリトライ設定"""

    max_retries: int = 3
    base_delay: float = 1.0

    def delay_for_attempt(self, attempt: int) -> float:
        """指数バックオフ風（線形）遅延"""
        return self.base_delay * (attempt + 1)


@dataclass
class AuditResult:
    """監査結果（正規化済み）"""

    score: float
    passed: bool
    issues: List[str]
    improvements: List[str]
    needs_human_review: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
