"""
tests/api/test_easy_mode_security_guards.py
Part 3 (Step 9, 11-12) リグレッション防止テスト:
Easy Mode 高負荷エンドポイント（gacha, reverse-generate, task cancel）の
APIキー認証ガードおよび不正 task_id バリデーションを検証。
"""

from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from src.backend.server import app
from src.backend.config import settings

client = TestClient(app)


def test_gacha_endpoint_requires_auth():
    """認証ヘッダーなし、または不正キーで /easy_mode/gacha を呼ぶと 401 が返ることを検証"""
    orig_disabled = settings.AUTH_DISABLED
    orig_keys = getattr(settings, "ALLOWED_API_KEYS", "")
    try:
        settings.AUTH_DISABLED = False
        settings.ALLOWED_API_KEYS = "valid-test-key"

        # 認証なし
        res = client.post("/easy_mode/gacha", json={"keywords": ["異世界", "チート"]})
        assert res.status_code == 401

        # 不正キー
        res = client.post(
            "/easy_mode/gacha",
            json={"keywords": ["異世界", "チート"]},
            headers={"Authorization": "Bearer invalid-key"},
        )
        assert res.status_code == 401
    finally:
        settings.AUTH_DISABLED = orig_disabled
        settings.ALLOWED_API_KEYS = orig_keys


def test_cancel_task_rejects_malformed_task_id():
    """特殊記号やパストラバーサルを含む task_id が 422 で拒絶されることを検証"""
    orig_disabled = settings.AUTH_DISABLED
    orig_keys = getattr(settings, "ALLOWED_API_KEYS", "")
    try:
        settings.AUTH_DISABLED = False
        settings.ALLOWED_API_KEYS = "valid-test-key"

        headers = {"Authorization": "Bearer valid-test-key"}

        # 不正な記号 (スラッシュやドットを含むパストラバーサル的ID)
        # Note: FastAPI/Starlette では URL path 内のスラッシュはルーティングエラーになるため
        # 特殊記号（%やスペース等）を検証
        res = client.delete("/easy_mode/task/task%20invalid", headers=headers)
        assert res.status_code == 422
    finally:
        settings.AUTH_DISABLED = orig_disabled
        settings.ALLOWED_API_KEYS = orig_keys


def test_cancel_task_requires_auth():
    """/easy_mode/task/{task_id} が認証なしで 401 を返すことを検証"""
    orig_disabled = settings.AUTH_DISABLED
    orig_keys = getattr(settings, "ALLOWED_API_KEYS", "")
    try:
        settings.AUTH_DISABLED = False
        settings.ALLOWED_API_KEYS = "valid-test-key"

        res = client.delete("/easy_mode/task/valid_task_123")
        assert res.status_code == 401
    finally:
        settings.AUTH_DISABLED = orig_disabled
        settings.ALLOWED_API_KEYS = orig_keys
