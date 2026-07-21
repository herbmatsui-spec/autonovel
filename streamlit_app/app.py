"""
app.py - 覇権小説自動生成ツール v3.0 エントリーポイント
起動方法:
    streamlit run app.py
"""
from __future__ import annotations

import logging
app = __import__(__name__)
import warnings

import streamlit as st
try:
    from streamlit.errors import StreamlitAPIException
except ImportError:
    StreamlitAPIException = Exception

# ==========================================
# アプリ初期化
# ==========================================
try:
    st.set_page_config(
        page_title="覇権小説エンジン v3.0 | 次世代AIナラティブエンジニアリング",
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except StreamlitAPIException:
    pass

warnings.filterwarnings("ignore")
from config.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# --- リファクタリング後のインポート ---
from src.core.plugin_loader import PluginLoader
from streamlit_app.health_check import ensure_backend_available_sync
from streamlit_app.landing import render_landing
from streamlit_app.sidebar import render_sidebar
from streamlit_app.state import UIStateStore

DEFAULT_APP_MODE = "easy"
DEFAULT_DESIRES = ["カタルシス"]

def _init_session() -> None:
    """型安全なセッション状態の初期値設定"""
    # 1. RuntimeState の初期化
    runtime = UIStateStore.get_runtime()
    if runtime.app_mode is None:
        runtime.app_mode = DEFAULT_APP_MODE

    if not runtime.token_stats:
        runtime.token_stats = {"prompt": 0, "completion": 0, "calls": 0}
    if not runtime.forbidden_patterns:
        runtime.forbidden_patterns = []
    if not runtime.selected_desires:
        runtime.selected_desires = DEFAULT_DESIRES

    # 2. UIState の初期化 (UIStateStore経由で自動的にUIStateモデルが作成される)
    # ここでデフォルトのUI状態を設定する場合に利用
    UIStateStore().update_ui_state(active_tab="home")

def _run_navigation(api_key: str) -> None:
    """Gemini APIキーを使用してエンジンを初期化し、ナビゲーションメニューを実行する。"""
    try:
        # EngineService.get_instance 等を利用して、シングルトンまたはキャッシュされたサービスを取得する
        from src.engine_service import EngineService
        # 既存の EngineService は api_key ベースでインスタンスをキャッシュしているため、これを利用
        service = EngineService.get_instance(api_key=api_key)

        # 必要に応じて NovelService (未提供) へのブリッジを行う

    except Exception as e:
        # TODO: エラーハンドリングの移行
        from streamlit_app.utils.errors import AppErrorHandler
        AppErrorHandler.handle(e, "エンジンの初期化に失敗しました")
        return

    from streamlit_app.pages_config import get_pages
    pages_dict = get_pages()

    mode = UIStateStore.get_runtime().app_mode
    page_key = "かんたんモード" if mode == "easy" else "上級者モード"

    pages = pages_dict.get(page_key, [])
    if pages:
        pg = st.navigation(pages)
        pg.run()
    else:
        st.error("ページが見つかりません。")

def main() -> None:
    """メインエントリーポイント"""
    # 高級感のあるフローティングサイドバーCSSの注入
    with open("streamlit_app/ui/static/styles.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # 状態変更イベントの登録
    UIStateStore.subscribe("active_job", lambda job: st.toast("🚀 バックグラウンド処理を開始しました", icon="⚙️"))

    # プラグインの初期化
    PluginLoader.get_instance().load_all_plugins()

    # 設定ファイルの変更監視

    _init_session()

    # バックエンドの死活監視
    if not ensure_backend_available_sync():
        return

    if UIStateStore.get_runtime().backend_connection_error:
        from streamlit_app.utils.errors import AppErrorHandler
        AppErrorHandler.show_connection_error()

    with st.sidebar:
        api_key = render_sidebar()

    if not api_key:
        render_landing()
        # APIキーがない場合はリソース状況などは表示しない
        st.sidebar.empty()
        return

    _run_navigation(api_key)

if __name__ == "__main__":
    main()
