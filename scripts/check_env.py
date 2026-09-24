"""AutoNovel 環境自己診断スクリプト (Step 2).

Python バージョン、仮想環境の有無、ポート空き状況 (8200, 5173) を
事前に検査し、前提条件不足時は明確な解決策を提示する。

実行:
    python scripts/check_env.py          # カラー表示
    python scripts/check_env.py --json   # JSON 出力

終了コード:
    0 : すべての前提条件を満たす
    1 : 1 つ以上の前提条件が未充足
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
import venv
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- 定数

MIN_PYTHON = (3, 12)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_PORTS = {
    8200: "Backend (Uvicorn)",
    5173: "Frontend (Vite dev server)",
}
REQUIRED_COMMANDS = ("python", "npm")


@dataclass
class CheckResult:
    """単一の検査結果。"""

    name: str
    ok: bool
    detail: str
    solution: str = ""


@dataclass
class EnvironmentReport:
    """環境診断レポート全体。"""

    ok: bool
    python_version: str
    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)
        self.ok = self.ok and result.ok


# ---------------------------------------------------------------- 検査ロジック


def check_python_version() -> CheckResult:
    """Python バージョンが >= 3.12 であること。"""
    current = sys.version_info[:2]
    version_str = ".".join(map(str, current))
    if current >= MIN_PYTHON:
        return CheckResult(
            name="python_version",
            ok=True,
            detail=f"Python {version_str} (required >= 3.12)",
        )
    return CheckResult(
        name="python_version",
        ok=False,
        detail=f"Python {version_str} is too old (required >= 3.12)",
        solution="Python 3.12 以降を https://www.python.org/ からインストールしてください。",
    )


def check_virtualenv() -> CheckResult:
    """プロジェクト直下に .venv が存在すること（無ければ作成可否のみ報告）。"""
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        return CheckResult(
            name="virtualenv",
            ok=True,
            detail=f"Virtual environment found: {venv_path}",
        )
    return CheckResult(
        name="virtualenv",
        ok=False,
        detail=f"Virtual environment not found: {venv_path}",
        solution="scripts/start_local.ps1 が自動作成します。手動の場合は `py -m venv .venv` を実行してください。",
    )


def check_port(port: int, label: str) -> CheckResult:
    """ポートが空いている（リッスン中のプロセスがいない）こと。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", port))
    if result != 0:
        return CheckResult(
            name=f"port_{port}",
            ok=True,
            detail=f"Port {port} ({label}) is free",
        )
    return CheckResult(
        name=f"port_{port}",
        ok=False,
        detail=f"Port {port} ({label}) is already in use",
        solution=(
            f"ポート {port} を占有しているプロセスを停止してください: "
            "`powershell -File scripts/stop_local.ps1` または "
            f"`Get-NetTCPConnection -LocalPort {port} | Select-Object OwningProcess` で特定。"
        ),
    )


def check_command(command: str) -> CheckResult:
    """必須コマンドが PATH 上に存在すること。"""
    path = shutil.which(command)
    if path:
        return CheckResult(
            name=f"command_{command}",
            ok=True,
            detail=f"'{command}' found at {path}",
        )
    return CheckResult(
        name=f"command_{command}",
        ok=False,
        detail=f"'{command}' not found in PATH",
        solution=(
            f"'{command}' を PATH に追加してください。"
            + ("Node.js を https://nodejs.org/ からインストールしてください。" if command == "npm" else "")
        ),
    )


def run_all_checks(ensure_venv: bool = False) -> EnvironmentReport:
    """全検査を実行してレポートを返す。"""
    report = EnvironmentReport(
        ok=True,
        python_version=".".join(map(str, sys.version_info[:2])),
    )
    report.add(check_python_version())
    report.add(check_command("python"))
    report.add(check_command("npm"))
    if ensure_venv and not (PROJECT_ROOT / ".venv").exists():
        # --ensure-venv 指定時は不足している仮想環境を自動作成する
        try:
            venv.create(PROJECT_ROOT / ".venv", with_pip=True)
        except OSError as exc:  # pragma: no cover - 環境依存
            report.add(
                CheckResult(
                    name="virtualenv",
                    ok=False,
                    detail=f"Failed to create venv: {exc}",
                    solution="ディスク容量・書き込み権限を確認してください。",
                )
            )
    report.add(check_virtualenv())
    for port, label in REQUIRED_PORTS.items():
        report.add(check_port(port, label))
    return report


# ---------------------------------------------------------------- 表示


def print_report(report: EnvironmentReport) -> None:
    """カラー表示でレポートを出力する。"""
    ok_mark = "\033[92mOK  \033[0m"
    ng_mark = "\033[91mFAIL\033[0m"
    print("=" * 64)
    print(" AutoNovel Environment Check")
    print("=" * 64)
    for result in report.results:
        mark = ok_mark if result.ok else ng_mark
        print(f" [{mark}] {result.name}: {result.detail}")
        if not result.ok and result.solution:
            print(f"        -> {result.solution}")
    print("-" * 64)
    if report.ok:
        print("\033[92m All prerequisites are satisfied. Ready to launch.\033[0m")
    else:
        print("\033[91m Some prerequisites are missing. Fix them and re-run.\033[0m")
    print("=" * 64)


def main(argv: list[str] | None = None) -> int:
    """エントリポイント。終了コードを返す。"""
    parser = argparse.ArgumentParser(description="AutoNovel environment self-check")
    parser.add_argument("--json", action="store_true", help="output report as JSON")
    parser.add_argument(
        "--ensure-venv",
        action="store_true",
        help="create .venv automatically when missing",
    )
    args = parser.parse_args(argv)

    report = run_all_checks(ensure_venv=args.ensure_venv)
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
