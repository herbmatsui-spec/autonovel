"""統合イラスト生成エンジンの配線ヘルパー（DI 是一点ここで集約）。

用途:
- `build_unified_illustration_generator()` で生成器を組み立てる
- `build_illustration_agent()` で既存 `IllustrationAgent` を初期化する
- `resolve_illustration_generator_step()` で Pipeline Step を作る
- `self_check()` で起動時に設定を検証する（失敗しても致命的ではない）

環境変数:
- `AUTONOVEL_IMAGE_MODEL`      : モデルキーの切替（既定 `nanobanana2lite`）
- `AUTONOVEL_IMAGE_MOCK`      : 疑似生成を強制
- `AUTONOVEL_ILLUSTRATION_LEGACY=1` : 旧 `ImageService` 経路へロールバック
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from config.image_models import (
    DEFAULT_IMAGE_MODEL,
    ENV_MODEL_KEY,
)
from src.services.illustration.clients import build_client
from src.services.illustration.config import (
    ENV_LEGACY,
    ENV_MOCK,
    UnifiedIllustrationConfig,
)
from src.services.illustration.unified_generator import UnifiedIllustrationGenerator

logger = logging.getLogger(__name__)

# API キーを設定から解決するための候補属性/キー
_API_KEY_ATTRS = ("get_gemini_api_key",)


def resolve_api_key(settings: Any = None) -> Optional[str]:
    """API キーを settings / 環境変数から解決する。"""
    if settings is not None:
        for attr in _API_KEY_ATTRS:
            getter = getattr(settings, attr, None)
            if callable(getter):
                try:
                    key = getter()
                    if key:
                        return str(key)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("settings.%s() failed: %s", attr, exc)
    import os

    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_GENAI_API_KEY")
        or os.getenv("NANOBANANA_API_KEY")
        or None
    )


def build_unified_illustration_config(
    settings: Any = None,
    **overrides: Any,
) -> UnifiedIllustrationConfig:
    """環境変数 + settings から設定を作る。"""
    config = UnifiedIllustrationConfig()
    key = resolve_api_key(settings)
    if key and not config.api_key:
        config.api_key = key
    for name, value in overrides.items():
        if value is not None:
            setattr(config, name, value)
    return config


def build_unified_illustration_generator(
    settings: Any = None,
    image_service: Any = None,
    llm: Any = None,
    **overrides: Any,
) -> UnifiedIllustrationGenerator:
    """統合エンジン（生成器）を組み立てる。

    Args:
        settings: backend settings（API キー解決に使う）。
        image_service: 旧 `ImageService`（ロールバック用途）。
        llm: 任意。6コマ要約の LLM 計画に使う。
        **overrides: `UnifiedIllustrationConfig` の上書き。
    """
    config = build_unified_illustration_config(settings, **overrides)
    generator = UnifiedIllustrationGenerator(
        config=config,
        llm=llm,
        image_service=image_service if (config.use_legacy_client or image_service) else None,
    )
    return generator


def build_illustration_agent(
    settings: Any = None,
    repo: Any = None,
    llm: Any = None,
    image_service: Any = None,
    **overrides: Any,
):
    """既存 `IllustrationAgent` を統合エンジン付きで初期化する。"""
    from src.agents.illustration_agent import IllustrationAgent

    config = build_unified_illustration_config(settings, **overrides)
    generator = UnifiedIllustrationGenerator(
        config=config,
        llm=llm,
        image_service=image_service if (config.use_legacy_client or image_service) else None,
    )
    return IllustrationAgent(
        image_service=image_service,
        config=config,
        generator=generator,
        repo=repo,
        llm=llm,
    )


def resolve_illustration_generator_step(generator: Any = None) -> Any:
    """`IllustrationPointGenerationStep` を生成器付きで組み立てる。"""
    from src.services.pipeline_steps import IllustrationPointGenerationStep

    return IllustrationPointGenerationStep(illustration_generator=generator)


def self_check(config: Optional[UnifiedIllustrationConfig] = None) -> Dict[str, Any]:
    """起動時チェック。例外は投げず、結果 dict を返す。

    モデルキーが未知なら警告して既定へ退回する（致命的ではない）。
    """
    result: Dict[str, Any] = {
        "ok": True,
        "model_key": None,
        "model_id": None,
        "client": None,
        "warnings": [],
    }
    try:
        cfg = config or build_unified_illustration_config()
        result["model_key"] = cfg.spec.key
        result["model_id"] = cfg.model_id
        result["client"] = cfg.spec.client
        result["mock_mode"] = cfg.mock_mode
        result["legacy"] = cfg.use_legacy_client
    except Exception as exc:  # noqa: BLE001
        result["ok"] = False
        result["warnings"].append(f"config resolution failed: {exc}")
        logger.warning("Illustration self-check: config resolution failed: %s", exc)
        return result

    if result["model_key"] != DEFAULT_IMAGE_MODEL and not result.get("legacy"):
        result["warnings"].append(
            f"non-default image model in use: {result['model_key']} ({result['model_id']})"
        )
        logger.info(
            "Illustration self-check: using non-default model %s (%s)",
            result["model_key"],
            result["model_id"],
        )

    try:
        client = build_client(
            result["model_key"],
            api_key=cfg.api_key,
            mock_mode=cfg.mock_mode,
        )
        result["client_name"] = getattr(client, "name", None)
        result["client_model_id"] = getattr(client, "model_id", None)
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"client build failed: {exc}")
        logger.warning("Illustration self-check: client build failed: %s", exc)

    return result


__all__ = [
    "DEFAULT_IMAGE_MODEL",
    "ENV_LEGACY",
    "ENV_MOCK",
    "ENV_MODEL_KEY",
    "build_illustration_agent",
    "build_unified_illustration_config",
    "build_unified_illustration_generator",
    "resolve_api_key",
    "resolve_illustration_generator_step",
    "self_check",
]
