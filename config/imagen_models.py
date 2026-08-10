"""Imagen 画像生成モデルのカタログ（SSOT: Single Source of Truth）。

モデルIDをコード内に散在させず、ここ一箇所だけで管理する。
実際のモデル選択（自動選択）は `select_imagen_model` でコンテキストに応じ決定される。
コード側は `fast` / `quality` / `ultra` というtierキーのみを扱い、
実際のAPIモデルIDへの変換は必ずこのモジュールを経由する。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ImagenTier(str, Enum):
    AUTO = "auto"
    FAST = "fast"
    QUALITY = "quality"
    ULTRA = "ultra"


@dataclass(frozen=True)
class ImagenModelSpec:
    key: str
    model_id: str
    tier_rank: int  # 1=最速, 3=最高品質
    description: str = ""


# 単一真理源: モデルIDはこの辞書にだけ書く
IMAGEN_MODEL_CATALOG: Dict[str, ImagenModelSpec] = {
    ImagenTier.FAST.value: ImagenModelSpec(
        "fast", "imagen-4.0-fast-generate-001", tier_rank=1, description="高速生成"
    ),
    ImagenTier.QUALITY.value: ImagenModelSpec(
        "quality", "imagen-4.0-generate-001", tier_rank=2, description="標準品質"
    ),
    ImagenTier.ULTRA.value: ImagenModelSpec(
        "ultra", "imagen-4.0-ultra-generate-001", tier_rank=3, description="最高品質"
    ),
}

DEFAULT_IMAGEN_TIER = ImagenTier.FAST.value


def get_imagen_model_id(tier_key: str) -> str:
    """tierキー(fast/quality/ultra)から実際のモデルIDを取得する。不明時はデフォルト。"""
    spec = IMAGEN_MODEL_CATALOG.get(tier_key)
    if spec is None:
        spec = IMAGEN_MODEL_CATALOG[DEFAULT_IMAGEN_TIER]
    return spec.model_id


def select_imagen_model(
    illustration_type: str,
    *,
    safety_level: str = "BLOCK_SOME",
    preferred: Optional[str] = None,
) -> str:
    """コンテキストから適切なImagenモデルIDを自動選択する。

    - preferred が有効なtierならそれを優先（明示指定）
    - それ以外は種別で自動選択:
        cover   / character -> ultra (品質重視)
        episode            -> fast  (速度・大量生成重視)
    - R15等の機微な表現を含む場合は fast を quality に引き上げ（品質・安全性確保）
    """
    if preferred and preferred in IMAGEN_MODEL_CATALOG:
        return IMAGEN_MODEL_CATALOG[preferred].model_id

    is_sensitive = safety_level == "R15_CONTENT"
    if illustration_type in ("cover", "character"):
        key = ImagenTier.ULTRA.value
    elif is_sensitive:
        key = ImagenTier.QUALITY.value
    else:
        key = ImagenTier.FAST.value
    return IMAGEN_MODEL_CATALOG[key].model_id
