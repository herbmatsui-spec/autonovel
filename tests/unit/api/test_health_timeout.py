"""Step 25 検証テスト: /health エンドポイントのタイムアウト最適化.

外部依存（Huey, Redis, DB）の1つが遅延してもヘルスチェックがタイムアウトしない
ことを検証する。各コンポーネントのタイムアウトは 1.0 秒に制限。
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

from src.backend.observability.health import (
    COMPONENT_TIMEOUT,
    build_health_payload,
    check_database,
    metrics,
)


class TestComponentTimeout:
    def test_component_timeout_is_one_second(self):
        """タイムアウト定数が 1.0 秒に制限されていること。"""
        assert COMPONENT_TIMEOUT == 1.0

    def test_slow_database_check_times_out(self):
        """DB チェックがタイムアウト時に DB_TIMEOUT を返すこと。

        5 秒かかるセッションに 0.1 秒のタイムアウトを渡し、
        タイムアウトが機能することを直接検証する。
        """

        class SlowSession:
            async def __aenter__(self):
                await asyncio.sleep(5)
                return self

            async def __aexit__(self, *args):
                return False

            async def execute(self, _query):
                return None

        class SlowMgr:
            def get_session(self):
                return SlowSession()

        with patch("src.backend.database.core.get_db_manager", return_value=SlowMgr()):
            start = time.monotonic()
            result = asyncio.run(check_database(timeout=0.1))
            elapsed = time.monotonic() - start

        assert result["code"] in ("DB_TIMEOUT", "DB_UNAVAILABLE")
        # 5 秒の遅延セッションが 1 秒未満で打ち切られること
        assert elapsed < 1.0, f"check_database took {elapsed:.2f}s"

    def test_health_payload_completes_within_timeout(self):
        """build_health_payload 全体がタイムアウト制限内で完了すること。"""
        metrics.reset_for_testing()
        start = time.monotonic()
        payload = asyncio.run(build_health_payload())
        elapsed = time.monotonic() - start

        assert payload["status"] in ("ok", "degraded")
        # 2 コンポーネント × 1.0 秒タイムアウトでも並行実行により 3 秒以内
        assert elapsed < 3.0, f"health payload took {elapsed:.2f}s"

    def test_health_payload_structure(self):
        """ヘルスペイロードの構造が正しいこと。"""
        metrics.reset_for_testing()
        payload = asyncio.run(build_health_payload())
        assert "database" in payload
        assert "huey" in payload
        assert "components" in payload
        assert "metrics" in payload

    def test_health_check_counter_incremented(self):
        """ヘルスチェック呼出でカウンタが加算されること。"""
        metrics.reset_for_testing()
        asyncio.run(build_health_payload())
        assert metrics.get("health_checks") >= 1
