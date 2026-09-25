"""Step 2 検証テスト: scripts/check_env.py の単体テスト。"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from check_env import (  # noqa: E402
    check_command,
    check_port,
    check_python_version,
    check_virtualenv,
    run_all_checks,
)


class TestPythonVersion:
    def test_current_python_passes(self):
        """実行中の Python は 3.12+ なのでパスする。"""
        result = check_python_version()
        assert result.ok is True

    def test_version_string_reported(self):
        result = check_python_version()
        assert result.detail.startswith("Python ")


class TestVirtualenv:
    def test_missing_venv_reports_solution(self):
        with patch("check_env.PROJECT_ROOT", Path("/nonexistent")):
            result = check_virtualenv()
        assert result.ok is False
        assert result.solution != ""

    def test_existing_venv_passes(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        with patch("check_env.PROJECT_ROOT", tmp_path):
            result = check_virtualenv()
        assert result.ok is True


class TestPortCheck:
    def test_free_port_passes(self):
        # 空いているポートを動的に確保して検査
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        result = check_port(free_port, "test")
        assert result.ok is True

    def test_bound_port_fails(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen(1)
            port = blocker.getsockname()[1]
            result = check_port(port, "test")
        assert result.ok is False
        assert "already in use" in result.detail


class TestCommandCheck:
    def test_python_found(self):
        result = check_command("python")
        assert result.ok is True

    def test_unknown_command_fails(self):
        result = check_command("definitely-not-a-command-xyz")
        assert result.ok is False
        assert result.solution != ""


class TestRunAllChecks:
    def test_report_structure(self):
        report = run_all_checks()
        assert report.ok is True
        names = [r.name for r in report.results]
        assert "python_version" in names
        assert "virtualenv" in names
        assert "port_8200" in names
        assert "port_5173" in names
