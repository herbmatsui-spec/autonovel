"""画像生成モデルカタログ（SSOT: Single Source of Truth）。

統合イラスト生成エンジン（`src/services/illustration/unified_generator.py`）が
参照する**唯一の**モデル定義場所。モデルID・クライアント種別・単価・機能対応を
ここに集約し、コード中の他釈所には一切書かない。

- 既定モデルは NanoBanana2Lite（`gemini-3.1-flash-lite-image`）。
- Imagen 系は切替候補／後方互換としてカタログに**残す**。
- 実環境の切替は環境変数 `AUTONOVEL_IMAGE_MODEL` 1つで行う（コード改変ゼロ）。

関連: `config/imagen_models.py` は旧 Imagen 専用カタログ。
本モジュールへの移行は段階的に進め、既存テストを壊さないため当面两者併存する。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional


# クライアント種別（`src/services/illustration/clients/` の実装クラスに対応する）
CLIENT_GEMINI_IMAGE = "gemini_image"
CLIENT_LEGACY_IMAGEN = "legacy_imagen"
CLIENT_MOCK = "mock"

# 環境変数名
ENV_MODEL_KEY = "AUTONOVEL_IMAGE_MODEL"


@dataclass(frozen=True)
class ImageModelSpec:
    """1モデル分の仕様。すべての生成設定はここへ集約する。"""

    key: str
    model_id: str
    client: str
    cost_per_image_usd: float = 0.034
    default_aspect_ratio: str = "3:4"
    supports_negative_prompt: bool = True
    supports_reference_images: bool = False
    supports_multi_panel_grid: bool = False
    description: str = ""


# 単一真理源: モデルIDはこの辞書だけに書く
IMAGE_MODEL_CATALOG: Dict[str, ImageModelSpec] = {
    # ---- 既定（NanoBanana2Lite） ----
    "nanobanana2lite": ImageModelSpec(
        key="nanobanana2lite",
        model_id="gemini-3.1-flash-lite-image",
        client=CLIENT_GEMINI_IMAGE,
        cost_per_image_usd=0.034,
        default_aspect_ratio="3:4",
        supports_negative_prompt=True,
        supports_reference_images=True,
        supports_multi_panel_grid=True,
        description="既定モデル。1話1枚の漫画シート（マルチパネルグリッド）に対応",
    ),
    # ---- Imagen 系（切替候補・後方互換） ----
    "imagen_fast": ImageModelSpec(
        key="imagen_fast",
        model_id="imagen-4.0-fast-generate-001",
        client=CLIENT_LEGACY_IMAGEN,
        cost_per_image_usd=0.03,
        default_aspect_ratio="3:4",
        supports_negative_prompt=True,
        description="高速生成（従来 tier: fast）",
    ),
    "imagen_quality": ImageModelSpec(
        key="imagen_quality",
        model_id="imagen-4.0-generate-001",
        client=CLIENT_LEGACY_IMAGEN,
        cost_per_image_usd=0.07,
        default_aspect_ratio="3:4",
        supports_negative_prompt=True,
        description="標準品質（従来 tier: quality）",
    ),
    "imagen_ultra": ImageModelSpec(
        key="imagen_ultra",
        model_id="imagen-4.0-ultra-generate-001",
        client=CLIENT_LEGACY_IMAGEN,
        cost_per_image_usd=0.20,
        default_aspect_ratio="3:4",
        supports_negative_prompt=True,
        description="最高品質（従来 tier: ultra）",
    ),
    # ---- テスト専用 ----
    "mock": ImageModelSpec(
        key="mock",
        model_id="mock",
        client=CLIENT_MOCK,
        cost_per_image_usd=0.0,
        supports_negative_prompt=True,
        supports_reference_images=True,
        supports_multi_panel_grid=True,
        description="疑似画像生成（CI・オフライン検証用）",
    ),
}

# 既定モデルキー
DEFAULT_IMAGE_MODEL: str = "nanobanana2lite"

# 旧 tier 名（fast/quality/ultra/auto）→ 新カタログキーへの写像（後方互換）
_LEGACY_TIER_ALIASES: Dict[str, str] = {
    "auto": DEFAULT_IMAGE_MODEL,
    "fast": "imagen_fast",
    "quality": "imagen_quality",
    "ultra": "imagen_ultra",
    "default": DEFAULT_IMAGE_MODEL,
    # 旧 Imagen モデルIDが直接指定された場合も受け付ける
    "imagen-4.0-fast-generate-001": "imagen_fast",
    "imagen-4.0-generate-001": "imagen_quality",
    "imagen-4.0-ultra-generate-001": "imagen_ultra",
    "gemini-3.1-flash-lite-image": "nanobanana2lite",
}


def normalize_model_key(key: Optional[str]) -> str:
    """任意の指定（tier名・モデルID・None）をカタログキーへ正規化する。

    未知の値は黙って既定へ倒さず、呼び出し側が判定できるようそのまま返す。
    """
    if not key:
        return DEFAULT_IMAGE_MODEL
    raw = str(key).strip()
    lowered = raw.lower()
    if lowered in IMAGE_MODEL_CATALOG:
        return lowered
    return _LEGACY_TIER_ALIASES.get(lowered, raw)


def get_image_model_spec(key: Optional[str]) -> ImageModelSpec:
    """カタログキーから仕様を返す。不明時は既定モデルへフォールバックする。"""
    normalized = normalize_model_key(key)
    spec = IMAGE_MODEL_CATALOG.get(normalized)
    if spec is None:
        spec = IMAGE_MODEL_CATALOG[DEFAULT_IMAGE_MODEL]
    return spec


def get_image_model_id(key: Optional[str]) -> str:
    """カタログキーから実モデルIDを返す（旧 `get_imagen_model_id` 相当）。"""
    return get_image_model_spec(key).model_id


def resolve_model_key_from_env(default: str = DEFAULT_IMAGE_MODEL) -> str:
    """環境変数 `AUTONOVEL_IMAGE_MODEL` から実効モデルキーを決定する。

    未設定・空文字なら `default`（既定は NanoBanana2Lite）。
    未知の値が設定されていた場合は警告ログを出しつつ既定へ倒す。
    """
    raw = os.getenv(ENV_MODEL_KEY, "").strip()
    if not raw:
        return normalize_model_key(default)

    normalized = normalize_model_key(raw)
    if normalized not in IMAGE_MODEL_CATALOG:
        import logging

        logging.getLogger(__name__).warning(
            "Unknown image model key %r (env %s); falling back to %s",
            raw,
            ENV_MODEL_KEY,
            DEFAULT_IMAGE_MODEL,
        )
        return DEFAULT_IMAGE_MODEL
    return normalized


def estimate_cost_usd(key: Optional[str], image_count: int = 1) -> float:
    """指定枚数の概算コスト（USD）を返す。"""
    spec = get_image_model_spec(key)
    return round(spec.cost_per_image_usd * max(0, int(image_count)), 6)


__all__ = [
    "CLIENT_GEMINI_IMAGE",
    "CLIENT_LEGACY_IMAGEN",
    "CLIENT_MOCK",
    "DEFAULT_IMAGE_MODEL",
    "ENV_MODEL_KEY",
    "IMAGE_MODEL_CATALOG",
    "ImageModelSpec",
    "estimate_cost_usd",
    "get_image_model_id",
    "get_image_model_spec",
    "normalize_model_key",
    "resolve_model_key_from_env",
]
