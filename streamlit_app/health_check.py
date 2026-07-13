"""
health_check.py - バックエンドの死活監視およびAPIキー検証ロジック
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

BACKEND_HEALTH_URL = "http://localhost:8200/health"
BACKEND_HEALTH_TIMEOUT_SEC = 2.0
BACKEND_STARTUP_WAIT_SEC = 10

async def check_backend_health() -> dict[str, str]:
    """バックエンドサーバーのヘルスステータスを取得する（非同期実装）"""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(BACKEND_HEALTH_URL, timeout=BACKEND_HEALTH_TIMEOUT_SEC)
            if res.status_code == 200:
                return res.json()
            return {"status": "error", "database": "unknown", "worker": "unknown"}
    except Exception:
        return {"status": "error", "database": "error", "worker": "error"}


async def validate_api_key_async(api_key: str) -> bool:
    """APIキーの非同期検証。"""
    from google import genai

    try:
        # google-genai SDKは現状同期的なため、run_in_executorで非同期化してイベントループをブロックしない
        def sync_validate():
            client = genai.Client(api_key=api_key)
            pager = client.models.list(config={"page_size": 1})
            next(iter(pager))
            return True

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, sync_validate)
    except Exception as e:
        logger.error(f"API Key validation failed: {e}")
        return False


async def ensure_backend_available() -> bool:
    """バックエンドサーバーの死活を監視し、接続不可の場合は自動起動を促すUIを表示する。
    本関数は非同期実装であり、呼び出し側は ``st.experimental_async`` で実行することを想定している。"""
    health_data = await check_backend_health()
    if health_data.get("status") == "ok":
        return True

    from streamlit_app.ui_utils import render_centered_title
    render_centered_title(
        "⚠️ システムステータス（バックエンド未接続）",
        "APIサーバーとの通信が確立されていません。以下の状態を確認・復旧してください。"
    )

    st.write("### 🔌 接続ダッシュボード")
    col1, col2, col3 = st.columns(3)
    api_status = health_data.get("status", "error")
    db_status = health_data.get("database", "error")
    worker_status = health_data.get("worker", "error")

    with col1:
        st.metric("APIサーバー", "🟢 稼働中" if api_status == "ok" else "🔴 停止中")
    with col2:
        st.metric("データベース", "🟢 正常" if db_status == "ok" else "🔴 エラー")
    with col3:
        st.metric("タスクワーカー", "🟢 稼働中" if worker_status == "ok" else "🔴 停止中")

    st.divider()
    st.write("バックエンドサーバーがダウンしているか、起動中です。")

    if st.button("🔄 バックエンドを自動起動する", type="primary"):
        from streamlit_app.backend_launcher import start_backend_processes
        with st.spinner("バックエンドを起動しています... (最大10秒待機)"):
            success = start_backend_processes()
            if success:
                # ポートが開くまで待機
                for _ in range(BACKEND_STARTUP_WAIT_SEC):
                    time.sleep(1)
                    if check_backend_health().get("status") == "ok":
                        break
                st.rerun()
            else:
                st.error("バックエンドの起動に失敗しました。ログを確認してください。")

    st.error("※ 自動起動で解決しない場合は、黒い画面（コマンドプロンプト）のプロセスを一度すべて終了させ、アプリフォルダ内の `run_all.bat` を直接ダブルクリックして再起動してください。")
    return False
