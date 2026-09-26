"""統合イラスト生成エンジンの設定。

**モデル差し替えはこのファイルの `model_key` 1行（または環境変数
`AUTONOVEL_IMAGE_MODEL`）だけで完結する。** コード改変は要らない。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from config.image_models import (
    DEFAULT_IMAGE_MODEL,
    ImageModelSpec,
    get_image_model_spec,
    resolve_model_key_from_env,
)

# 環境変数
ENV_MODEL_KEY = "AUTONOVEL_IMAGE_MODEL"
ENV_MOCK = "AUTONOVEL_IMAGE_MOCK"
ENV_LEGACY = "AUTONOVEL_ILLUSTRATION_LEGACY"


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in ("1", "true", "yes", "on")


@dataclass
class UnifiedIllustrationConfig:
    """全イラスト種別（表紙/挿絵/立ち絵/6コマ/24コマ）の共通設定。"""

    # ---- モデル（差し替えはここだけ） ----
    model_key: str = DEFAULT_IMAGE_MODEL

    # ---- 実行モード ----
    mock_mode: bool = False
    api_key: Optional[str] = None
    #: True のとき旧 `ImageService` 経路へロールバックする（緊急用）
    use_legacy_client: bool = False

    # ---- 出力 ----
    output_root: Path = Path("static/illustrations")
    default_aspect_ratio: str = "3:4"

    # ---- 後処理 ----
    enable_quality_gate: bool = True
    enable_upscale: bool = False
    enable_typesetting: bool = False
    upscale_factor: int = 2
    target_upscale_width: int = 2048
    typeset_grid_cols: int = 4
    typeset_grid_rows: int = 6
    font_size: int = 24

    # ---- キャラ参照 ----
    character_ref_dir: Path = Path("static/character_refs")
    enable_character_reference: bool = True

    # ---- リトライ ----
    max_retries: int = 2
    retry_backoff_sec: float = 0.5

    # ---- 種別ごとの既定アスペクト比 ----
    aspect_ratio_by_type: Dict[str, str] = field(
        default_factory=lambda: {
            "cover": "2:3",
            "character": "3:4",
            "episode": "3:4",
            "yonkoma": "3:4",
            "manga_24panel": "2:3",
        }
    )

    # ---- 品質ゲートの閾値（種別別に上書き可） ----
    quality_thresholds: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "default": {
                "min_grid_score": 0.0,       # 単発絵ではグリッド判定を行わない
                "min_sharpness": 0.15,
                "max_color_bleed": 0.35,
                "min_resolution": 256,
            },
            "multi_panel": {
                "min_grid_score": 0.0,       # 簡易実装のため既定は緩める
                "min_sharpness": 0.20,
                "max_color_bleed": 0.30,
                "min_resolution": 512,
            },
        }
    )

    def __post_init__(self) -> None:
        self.output_root = Path(self.output_root)
        self.character_ref_dir = Path(self.character_ref_dir)
        # 環境変数が明示されていればそちらを優先（1行差し替え運用）
        env_model = os.getenv(ENV_MODEL_KEY, "").strip()
        if env_model:
            self.model_key = resolve_model_key_from_env(self.model_key)
        if _env_flag(ENV_MOCK):
            self.mock_mode = True
        if _env_flag(ENV_LEGACY):
            self.use_legacy_client = True

    # ---- 解決済みプロパティ ----

    @property
    def spec(self) -> ImageModelSpec:
        """実効モデルのカタログ仕様。"""
        return get_image_model_spec(self.model_key)

    @property
    def model_id(self) -> str:
        """実効モデル ID（実IDはカタログにのみ定義する）。"""
        return self.spec.model_id

    @property
    def cost_per_image_usd(self) -> float:
        return self.spec.cost_per_image_usd

    def aspect_ratio_for(self, illustration_type: Any) -> str:
        """種別ごとの既定アスペクト比を返す。未知の種別は既定値。"""
        key = getattr(illustration_type, "value", illustration_type)
        return self.aspect_ratio_by_type.get(str(key), self.default_aspect_ratio)

    def thresholds_for(self, illustration_type: Any, multi_panel: bool = False) -> Dict[str, float]:
        """種別に対応する品質ゲート閾値を返す。"""
        bucket = "multi_panel" if multi_panel else "default"
        merged = dict(self.quality_thresholds.get("default", {}))
        merged.update(self.quality_thresholds.get(bucket, {}))
        return merged

    # ---- 構築 ----

    @classmethod
    def from_env(cls, **overrides: Any) -> "UnifiedIllustrationConfig":
        """環境変数を読み込んだ設定を作る（引数はすべて上書き）。"""
        base = cls()
        for key, value in overrides.items():
            if value is not None:
                setattr(base, key, value)
        return base


__all__ = [
    "ENV_LEGACY",
    "ENV_MOCK",
    "ENV_MODEL_KEY",
    "UnifiedIllustrationConfig",
]
