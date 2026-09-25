"""Manga generation data models.

1話1枚（24コマ漫画シート一括生成）およびオプション写植に対応したデータモデル定義。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class AspectRatio(str, Enum):
    RATIO_3_4 = "3:4"
    RATIO_2_3 = "2:3"
    RATIO_1_1 = "1:1"
    RATIO_16_9 = "16:9"


@dataclass
class CharacterReference:
    """キャラクター参照アセット定義。"""
    name: str
    master_image_path: Path
    description: str = ""


@dataclass
class SpeechBubble:
    """写植用フキダシ定義（オプション）。"""
    panel_index: int  # 0 to 23
    text: str
    speaker: str = ""
    # コマ内相対座標 (0.0 - 1.0)
    rel_x: float = 0.5
    rel_y: float = 0.5
    bubble_type: str = "normal"  # normal, shout, whisper, thought


@dataclass
class MangaEpisodeInput:
    """1話分の入力定義。"""
    episode_number: int
    title: str
    synopsis: str
    characters: List[str] = field(default_factory=list)
    setting: str = ""
    dialogues: List[SpeechBubble] = field(default_factory=list)
    aspect_ratio: AspectRatio = AspectRatio.RATIO_3_4


@dataclass
class QualityCheckResult:
    """品質ゲート判定結果。"""
    is_valid: bool
    grid_score: float
    line_sharpness_score: float
    color_bleed_score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class MangaPipelineResult:
    """1話分のパイプライン実行結果。"""
    episode_number: int
    raw_sheet_path: Optional[Path] = None
    upscaled_sheet_path: Optional[Path] = None
    final_output_path: Optional[Path] = None
    api_calls_count: int = 1
    estimated_cost_usd: float = 0.034
    typeset_applied: bool = False
    quality_result: Optional[QualityCheckResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
