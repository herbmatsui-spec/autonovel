"""ImageService の必須引数 / 振る舞いテスト。

Step 6: api_key 必須化の検証。
Step 32: R15 セーフティ閾値の検証。
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.models.illustration import SafetyLevel
from src.services.image_service import ImageService


def test_image_service_requires_api_key():
    """Step 6: api_key が空文字 / None なら ValueError。"""
    with pytest.raises(ValueError, match="non-empty api_key"):
        ImageService(api_key="")
    with pytest.raises(ValueError, match="non-empty api_key"):
        ImageService(api_key=None)  # type: ignore[arg-type]


def test_image_service_accepts_api_key():
    """正常な api_key なら genai.Client が呼ばれる (mock 化で実 API 抑止)。"""
    with patch("src.services.image_service.genai.Client") as mock_client:
        svc = ImageService(api_key="test-key-xxx")
        assert svc.storage_dir == "static/illustrations"
        mock_client.assert_called_once_with(api_key="test-key-xxx")


def test_image_service_r15_safety_block_most():
    """Step 32: R15_CONTENT は BLOCK_MOST にマップされる。"""
    with patch("src.services.image_service.genai.Client"):
        svc = ImageService(api_key="k")
        settings = svc._build_safety_settings(SafetyLevel.R15_CONTENT)
        assert settings[0].threshold == "BLOCK_MOST"


def test_image_service_block_some_default():
    """デフォルト (BLOCK_SOME) はそのまま BLOCK_SOME。"""
    with patch("src.services.image_service.genai.Client"):
        svc = ImageService(api_key="k")
        settings = svc._build_safety_settings(SafetyLevel.BLOCK_SOME)
        assert settings[0].threshold == "BLOCK_SOME"


def test_image_service_unknown_level_falls_back_to_block_some():
    """未知の level は BLOCK_SOME にフォールバック。"""
    with patch("src.services.image_service.genai.Client"):
        svc = ImageService(api_key="k")
        settings = svc._build_safety_settings("UNKNOWN_LEVEL")
        assert settings[0].threshold == "BLOCK_SOME"
