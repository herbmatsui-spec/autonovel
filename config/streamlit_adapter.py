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

from config.constants import (
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

# サイドバーのモデル選択に表示するプリセット一覧。
# デフォルトの Gemini/Gemma に加え、OpenRouter で利用可能な代表的な
# OpenAI互換モデルを含める。「/」を含むIDは OpenAI互換プロバイダへルーティングされる。
PRESET_MODELS = [
    # デフォルト（Gemini / Gemma）
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemma-4-31b-it",
    # OpenRouter の人気モデル
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4.1",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat",
    "qwen/qwen2.5-72b-instruct",
    "google/gemini-2.0-flash-001",
]

# モデル選択の「自由入力」オプション
CUSTOM_MODEL = "✏️ カスタム（自由入力）"


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

        def render_model_selector(config_key: str, label: str, help_text: str) -> None:
            """用途別モデル選択（プリセット + 自由入力）。"""
            current = self.get(config_key) or ""
            options = list(PRESET_MODELS)
            if current and current not in options:
                options.append(current)
            options.append(CUSTOM_MODEL)
            default_index = options.index(current) if current in options else 0

            choice = st.selectbox(label, options=options, index=default_index, help=help_text)
            if choice == CUSTOM_MODEL:
                custom = st.text_input(
                    f"{label}（カスタム）",
                    value=current,
                    key=f"custom_{config_key}",
                    help="OpenRouter 等のモデルIDを自由に入力できます（例: anthropic/claude-3.5-sonnet）。",
                )
                if custom and custom != current:
                    self.set(config_key, custom)
            elif choice != current:
                self.set(config_key, choice)

        st.subheader("🤖 モデル設定")
        st.caption(
            "各工程で使用するAIモデルを選択します。OpenRouter等のOpenAI互換モデルも指定可能です。"
        )
        render_model_selector(
            "model_planning",
            "📝 プロット用モデル",
            "企画立案・プロット生成時に使用するAIモデルを選択します。",
        )
        render_model_selector(
            "model_plot_expansion",
            "🔍 詳細プロット用モデル",
            "エピソードごとの詳細プロット展開時に使用するAIモデルを選択します。",
        )
        render_model_selector(
            "model_writing",
            "✍️ 執筆用モデル",
            "本文執筆（小説生成）時に使用するAIモデルを選択します。",
        )

        st.divider()

        st.subheader("🔑 OpenRouter / OpenAI互換プロバイダ")
        st.caption(
            "モデルに OpenAI互換モデル（「/」を含むIDや gpt/claude/llama 等）を選んだ場合に使用します。"
        )
        openrouter_key = st.text_input(
            "API Key",
            type="password",
            value=self.get("openai_api_key") or "",
            key="cfg_openai_api_key",
            help="OpenRouter 等の OpenAI互換 API キー（例: sk-or-...）。",
        )
        if openrouter_key != (self.get("openai_api_key") or ""):
            self.set("openai_api_key", openrouter_key)

        base_url = st.text_input(
            "API Base URL",
            value=self.get("openai_base_url") or "https://openrouter.ai/api/v1",
            key="cfg_openai_base_url",
            help="OpenAI互換エンドポイント。既定は OpenRouter。",
        )
        if base_url != (self.get("openai_base_url") or ""):
            self.set("openai_base_url", base_url)

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
