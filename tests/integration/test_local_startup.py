"""Step 7 検証テスト: ローカル起動プロセスの自動検証テスト.

start_local.ps1 が 3 つのプロセスを立ち上げ、ヘルスチェックが通ること、
stop_local.ps1 で正常停止することを検証する。

CI 環境では実際のプロセス起動を避けるため、スクリプトの存在・構文検査と
-ucre ("skip real launch") モードを提供する。
"""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
START_SCRIPT = PROJECT_ROOT / "scripts" / "start_local.ps1"
STOP_SCRIPT = PROJECT_ROOT / "scripts" / "stop_local.ps1"
BACKEND_URL = "http://localhost:8200/health"

# 実プロセス起動テストは明示的にオプトインした場合のみ実行
RUN_REAL_LAUNCH = "--run-real-launch" in sys.argv


class TestScriptPresence:
    """起動・停止スクリプトが存在し、妥当な構文を持つこと。"""

    def test_start_script_exists(self):
        assert START_SCRIPT.exists(), f"missing: {START_SCRIPT}"

    def test_stop_script_exists(self):
        assert STOP_SCRIPT.exists(), f"missing: {STOP_SCRIPT}"

    def test_start_script_sets_sqlite_env(self):
        """HUEY_BACKEND=sqlite と DATABASE_URL が確実にセットされること。"""
        content = START_SCRIPT.read_text(encoding="utf-8")
        assert '$env:HUEY_BACKEND = "sqlite"' in content
        assert "sqlite:///./autonovel.db" in content

    def test_start_script_has_no_skip_migrations_flag(self):
        """ワーカー起動に --skip-migrations フラグが残っていないこと。"""
        content = START_SCRIPT.read_text(encoding="utf-8")
        # huey_consumer 起動行に skip-migrations を含めない
        worker_lines = [ln for ln in content.splitlines() if "huey_consumer" in ln]
        assert worker_lines, "huey_consumer launch line not found"
        for line in worker_lines:
            assert "--skip-migrations" not in line

    def test_start_script_invokes_init_db(self):
        """安全マイグレーション (init_db.py) を呼び出すこと。"""
        content = START_SCRIPT.read_text(encoding="utf-8")
        assert "init_db.py" in content

    def test_stop_script_targets_ports(self):
        """stop_local.ps1 がポート 8200 / 5173 を対象とすること。"""
        content = STOP_SCRIPT.read_text(encoding="utf-8")
        assert "8200" in content
        assert "5173" in content


class TestDryRun:
    """-DryRun モードが正常終了し、プロセスを起動しないこと。"""

    def test_dry_run_exits_zero(self):
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_SCRIPT),
                "-DryRun",
                "-SkipInstall",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"DryRun failed (rc={result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    def test_dry_run_lists_all_services(self):
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_SCRIPT),
                "-DryRun",
                "-SkipInstall",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        assert "uvicorn src.backend.server:app" in output
        assert "huey_consumer src.backend.tasks.huey.huey" in output
        assert "npm run dev" in output


class TestBatchWrapper:
    """アプリ起動_ローカル.bat が start_local.ps1 の薄いラッパーであること。"""

    def test_batch_wrapper_calls_powershell(self):
        bat = PROJECT_ROOT / "アプリ起動_ローカル.bat"
        assert bat.exists()
        content = bat.read_text(encoding="utf-8")
        assert "start_local.ps1" in content
        assert "-ExecutionPolicy" in content or "ExecutionPolicy" in content

    def test_stop_batch_wrapper_calls_powershell(self):
        bat = PROJECT_ROOT / "アプリ停止.bat"
        assert bat.exists()
        content = bat.read_text(encoding="utf-8")
        assert "stop_local.ps1" in content


@pytest.mark.skipif(not RUN_REAL_LAUNCH, reason="real launch disabled by default (use --run-real-launch)")
class TestRealLaunch:
    """実プロセス起動テスト（オプトイン）。ローカル環境でのみ実行。"""

    def test_backend_health_and_graceful_stop(self):
        """start_local.ps1 → /health 200 OK → stop_local.ps1 で正常停止。"""
        # 1) 起動
        launch = subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_SCRIPT),
                "-SkipInstall",
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # 2) ヘルスチェックが 200 を返すまで待機（最大 90 秒）
        health_ok = False
        try:
            for _ in range(90):
                try:
                    with urllib.request.urlopen(BACKEND_URL, timeout=2) as resp:
                        if resp.status == 200:
                            health_ok = True
                            break
                except (urllib.error.URLError, ConnectionError, OSError):
                    pass
                import time

                time.sleep(1)
        finally:
            # 3) 停止スクリプトで正常停止
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(STOP_SCRIPT),
                ],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            launch.wait(timeout=30)

        assert health_ok, f"backend health check did not return 200: {BACKEND_URL}"
