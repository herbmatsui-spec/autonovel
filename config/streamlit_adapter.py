"""
config/streamlit_adapter.py — Streamlit 環境向け設定アダプター

このモジュールは Streamlit に依存する設定管理機能を提供します。
CLI やテストからはインポートしないでください。
"""
from __future__ import annotations

import logging
from typing import Any

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from config.base import (
    SAFE_APPEND_MODE_DEFAULT,
    SAFE_APPEND_MODE_OPTIONS,
)
from config.models import GlobalConfigModel
from config.project_context import (
    GlobalConfig,
    get_config,
    set_config,
)

logger = logging.getLogger(__name__)


class StreamlitConfig(GlobalConfig):
    """
    Streamlit 実行環境専用の設定管理クラス。
    セッション状態との同期、UI コンポーネント表示を提供する。
    """

    def __init__(self):
        super().__init__()
        # 初期化時にセッション状態にデフォルト設定をロード
        if get_script_run_ctx() is not None:
            from streamlit_app.state import UIStateStore
            runtime_cfg = UIStateStore.get_runtime().config_data
            if not runtime_cfg:
                # get_config() を通じて TOML から読み込まれた設定を UIStateStore に同期
                UIStateStore.update_runtime("config_data", get_config().model_dump())

    def get(self, key: str, default=None):
        """設定値を取得する（セッション状態があれば優先）"""
        if get_script_run_ctx() is not None:
            from streamlit_app.state import UIStateStore
            cfg = UIStateStore.get_runtime().config_data
            if cfg:
                return cfg.get(key, default)
        return getattr(get_config(), key, default)

    def update(self, **kwargs) -> None:
        """複数の設定値を一括更新し、セッションおよび TOML へ反映する"""
        from streamlit_app.state import UIStateStore
        # 1. バリデーションとモデル更新
        current_cfg_dict = (
            UIStateStore.get_runtime().config_data or get_config().model_dump()
            if get_script_run_ctx() is not None
            else get_config().model_dump()
        )
        validated = GlobalConfigModel(**{**current_cfg_dict, **kwargs})

        # 2. メモリ上のグローバル設定を更新
        set_config(validated)

        # 3. Streamlit セッション状態を更新 (UIStateStore 経由)
        if get_script_run_ctx() is not None:
            UIStateStore.update_runtime("config_data", validated.model_dump())

        # 4. TOML ファイルへ永続化 (SSOT)
        self._persist_to_toml(validated)

    @staticmethod
    def _get_widget_value(widget_key: str) -> Any:
        """
        Streamlit ウィジェットの状態を読み取るラッパー。
        st.session_state へのアクセスをこの1箇所に閉じ込める。
        """
        return st.session_state.get(widget_key)

    def display_sidebar(self) -> None:
        """Streamlit サイドバーに設定 UI を描画する"""
        st.header("⚙️ 詳細設定（Config）")

        def _sync(key: str, widget_key: str):
            value = StreamlitConfig._get_widget_value(widget_key)
            if value is not None:
                self.set(key, value)

        models = [
            "gemini-3.1-flash-lite-preview",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.1-pro",
            "gemma-4-31b-it",
        ]

        curr_planning = self.get("model_planning")
        if curr_planning and curr_planning not in models:
            models.append(curr_planning)

        curr_writing = self.get("model_writing")
        if curr_writing and curr_writing not in models:
            models.append(curr_writing)

        st.subheader("🤖 モデル設定")
        st.selectbox(
            "企画用モデル",
            options=models,
            index=models.index(curr_planning) if curr_planning in models else 0,
            key="cfg_model_planning",
            on_change=lambda: _sync("model_planning", "cfg_model_planning"),
            help="企画立案やプロット生成時に使用するAIモデルを選択します。",
        )
        st.selectbox(
            "執筆用モデル",
            options=models,
            index=models.index(curr_writing) if curr_writing in models else 0,
            key="cfg_model_writing",
            on_change=lambda: _sync("model_writing", "cfg_model_writing"),
            help="本文執筆（小説生成）時に使用するAIモデルを選択します。",
        )

        st.divider()

        st.subheader("🔄 動作設定")
        st.number_input(
            "履歴最大保持数",
            min_value=1,
            max_value=100,
            value=self.get("max_history_len", 30),
            key="cfg_max_history_len",
            on_change=lambda: _sync("max_history_len", "cfg_max_history_len"),
            help="メモリやコンテキストとして保持するエピソード履歴の最大数です。",
        )
        st.sidebar.number_input(
            "最大並行処理数 (0=Auto)",
            min_value=0,
            max_value=20,
            value=self.get("max_concurrency", 0),
            key="cfg_max_concurrency",
            on_change=lambda: _sync("max_concurrency", "cfg_max_concurrency"),
            help="同時に実行する最大APIタスク数です。0を設定すると、CPUコア数に応じて自動的に最適化されます。",
        )
        st.sidebar.selectbox(
            "安全追加モード",
            options=SAFE_APPEND_MODE_OPTIONS,
            index=SAFE_APPEND_MODE_OPTIONS.index(
                self.get("safe_append_mode", SAFE_APPEND_MODE_DEFAULT)
            ),
            key="cfg_safe_append_mode",
            on_change=lambda: _sync("safe_append_mode", "cfg_safe_append_mode"),
            help="テキスト追加時にトークン上限を超えそうな場合の挙動（自動調整、警告のみ、エラー終了）を設定します。",
        )

        st.sidebar.divider()

        st.sidebar.subheader("📁 保存設定")
        st.sidebar.toggle(
            "自動バックアップ",
            value=self.get("auto_backup", True),
            key="cfg_auto_backup",
            on_change=lambda: _sync("auto_backup", "cfg_auto_backup"),
            help="データを更新する際に、自動的にデータベースのバックアップを作成します。",
        )

