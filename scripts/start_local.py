"""AutoNovel ローカル起動スクリプト (Python版クロスプラットフォームランチャー)。

バックエンド (Uvicorn)、ワーカー (Huey)、フロントエンド (Vite) を同時に起動し、
終了時はすべてのプロセスを安全に停止します。
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def main() -> None:
    print("=" * 50)
    print("  AutoNovel Local Launcher")
    print("=" * 50)
    print("  Frontend UI : http://localhost:5173")
    print("  Backend API : http://localhost:8200")
    print("  API Docs    : http://localhost:8200/docs")
    print("=" * 50)

    # 仮想環境 Python の優先利用
    venv_python = sys.executable

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)

    processes: list[subprocess.Popen] = []

    try:
        # 1. バックエンド起動
        print("\n[1/3] バックエンド (FastAPI / Uvicorn) を起動中...")
        backend_proc = subprocess.Popen(
            [venv_python, "-m", "uvicorn", "src.backend.server:app", "--reload", "--port", "8200"],
            cwd=str(ROOT_DIR),
            env=env,
        )
        processes.append(backend_proc)

        # 2. Huey ワーカー起動
        print("[2/3] Huey 非同期ワーカーを起動中...")
        worker_proc = subprocess.Popen(
            [venv_python, "-m", "huey.bin.huey_consumer", "src.backend.tasks.huey.huey"],
            cwd=str(ROOT_DIR),
            env=env,
        )
        processes.append(worker_proc)

        # 3. フロントエンド起動
        print("[3/3] フロントエンド (Vite Dev Server) を起動中...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(FRONTEND_DIR),
            env=env,
        )
        processes.append(frontend_proc)

        print("\n✨ すべてのサービスが正常に起動しました。")
        print("停止するには Ctrl+C を押してください。\n")

        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️ プロセス (PID: {p.pid}) が終了しました。")

    except KeyboardInterrupt:
        print("\n🛑 サービスを停止しています...")
    finally:
        for p in processes:
            try:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
            except Exception:
                pass
        print("✅ すべてのサービスを停止しました。")


if __name__ == "__main__":
    main()
