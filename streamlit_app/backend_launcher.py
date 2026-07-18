"""
streamlit_app/backend_launcher.py — バックエンド API サーバーの起動を管理する。
uvicorn を使って FastAPI アプリをサブプロセスで起動し、起動完了を待機する。
"""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from typing import Optional

logger = logging.getLogger(__name__)

_BACKEND_HOST = "127.0.0.1"
_BACKEND_PORT = 8200  # must match docker-compose.yml
_BACKEND_URL = f"http://{_BACKEND_HOST}:{_BACKEND_PORT}/health"
_STARTUP_TIMEOUT = 30.0  # 秒

def _find_backend_entrypoint() -> str:
    """バックエンドの FastAPI エントリポイントを探す。"""
    # プロジェクトルートからの相対パスを試行
    candidates = [
        "src/backend/server.py",
        "server.py",
    ]
    for c in candidates:
        if __import__("os").path.exists(c):
            return c
    raise FileNotFoundError("Backend entrypoint not found")


def start_backend() -> Optional[subprocess.Popen]:
    """バックエンドサーバーを起動する。すでに起動済みの場合は None を返す。"""
    try:
        import requests  # noqa: F401
    except Exception:
        logger.warning("requests is not installed; cannot check backend health. Install 'requests' to enable backend launcher.")
        return None

    # 簡易的な起動済みチェック
    try:
        import requests as req
        resp = req.get(_BACKEND_URL, timeout=2)
        if resp.status_code == 200:
            logger.info("Backend is already running.")
            return None
    except Exception:
        pass

    entry = _find_backend_entrypoint()
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.backend.server:app",
        "--host", _BACKEND_HOST,
        "--port", str(_BACKEND_PORT),
        "--log-level", "info",
    ]
    logger.info(f"Starting backend server: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as e:
        logger.error(f"Failed to start backend process: {e}")
        return None

    # 起動待機
    deadline = time.time() + _STARTUP_TIMEOUT
    while time.time() < deadline:
        try:
            resp = req.get(_BACKEND_URL, timeout=2)
            if resp.status_code == 200:
                logger.info("Backend started successfully.")
                return proc
        except Exception:
            time.sleep(0.5)
    logger.error("Backend did not become ready within timeout.")
    return proc
