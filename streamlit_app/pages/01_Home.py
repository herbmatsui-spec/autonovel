"""
streamlit_app/pages/01_Home.py — ダッシュボード＆設定ホーム画面

このファイルがStreamlitアプリの最初の画面になります。
左サイドメニューから設定タブを選択できます。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.models import GlobalConfigModel
from streamlit_app.state import ConfigState, UIStateStore

st.set_page_config(
    page_title="AutoNovel - ホーム",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRESET_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemma-4-31b-it",
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

COST_MODE_OPTIONS = {
    "quality": "🧠 品質優先 (高性能モデル使用)",
    "balanced": "⚖️ バランス (品質とコストのトレードオフ)",
    "cost_priority": "💰 コスト優先 (軽量モデル使用)",
}

SAFETY_OPTIONS = {
    "BLOCK_NONE": "🔓 制限なし",
    "BLOCK_ONLY_HIGH": "⚠️ 高リスクのみブロック (推奨)",
    "BLOCK_ALL": "🔒 全リスクブロック",
}


def load_config() -> GlobalConfigModel:
    try:
        from config.project_context import get_config
        return get_config()
    except Exception:
        return GlobalConfigModel.default()


def render_sidebar_settings():
    """サイドバー設定パネル"""
    st.sidebar.title("⚙️ 設定")

    cfg = load_config()

    with st.sidebar.expander("🤖 LLMモデル設定", expanded=True):
        st.caption("各工程で使用するAIモデルを設定します")

        model_configs = {
            "model_writing": ("✍️ 執筆モデル", "本文執筆時に使用"),
            "model_planning": ("📝 プロットモデル", "企画立案時に使用"),
            "model_plot_expansion": ("🔍 詳細展開モデル", "プロット詳細展開時に使用"),
            "model_climax": ("🔥 クライマックスモデル", "高潮場面の執筆時に使用"),
        }

        for key, (label, help_text) in model_configs.items():
            current = getattr(cfg, key, "") or ""
            options = list(PRESET_MODELS)
            if current and current not in options:
                options.insert(0, current)

            selected = st.selectbox(
                label,
                options=options,
                index=options.index(current) if current in options else 0,
                key=f"cfg_{key}",
                help=help_text,
            )
            if selected != current:
                st.session_state[f"_pending_{key}"] = selected

    with st.sidebar.expander("🔑 API設定", expanded=False):
        st.text_input(
            "OpenAI/API Key",
            type="password",
            value=cfg.openai_api_key or "",
            key="cfg_openai_api_key",
            help="OpenRouter等のOpenAI互換APIキー",
        )
        st.text_input(
            "API Base URL",
            value=cfg.openai_base_url or "https://openrouter.ai/api/v1",
            key="cfg_openai_base_url",
            help="OpenAI互換エンドポイント",
        )

    with st.sidebar.expander("💰 コスト管理", expanded=False):
        cost_mode = st.selectbox(
            "コストモード",
            options=list(COST_MODE_OPTIONS.keys()),
            format_func=lambda x: COST_MODE_OPTIONS[x],
            index=list(COST_MODE_OPTIONS.keys()).index(
                getattr(cfg, "cost_mode", "balanced") or "balanced"
            ),
            key="cfg_cost_mode",
        )
        st.caption("品質とコストのトレードオフを設定")

    with st.sidebar.expander("🔒 安全・フィルタ設定", expanded=False):
        enable_nsfw = st.toggle(
            "NSFW/官能コンテンツ許可",
            value=getattr(cfg, "enable_nsfw", False),
            key="cfg_enable_nsfw",
        )
        safety_level = st.selectbox(
            "セーフティレベル",
            options=list(SAFETY_OPTIONS.keys()),
            format_func=lambda x: SAFETY_OPTIONS[x],
            index=list(SAFETY_OPTIONS.keys()).index(
                getattr(cfg, "safety_filter_level", "BLOCK_ONLY_HIGH") or "BLOCK_ONLY_HIGH"
            ),
            key="cfg_safety_filter_level",
        )

    with st.sidebar.expander("🔧 機能开关", expanded=False):
        ConfigState.init_defaults()

        st.toggle(
            "📝 ドラフトポリシング",
            value=ConfigState.get("enable_draft_polish", True),
            key="cfg_enable_draft_polish",
            help="執筆後に文章を自動校正・洗練",
        )
        st.toggle(
            "🎭 アクタークォリティ",
            value=ConfigState.get("enable_actor_critic", True),
            key="cfg_enable_actor_critic",
            help="文章の品質をLLMに評価させる",
        )
        st.toggle(
            "🔍 詳細オーディット",
            value=ConfigState.get("enable_heavy_audit", True),
            key="cfg_enable_heavy_audit",
            help="追加の詳細品質チェックを実行",
        )

    with st.sidebar.expander("📁 保存設定", expanded=False):
        st.toggle(
            "自動バックアップ",
            value=getattr(cfg, "auto_backup", True),
            key="cfg_auto_backup",
        )
        st.number_input(
            "履歴最大保持数",
            min_value=1,
            max_value=100,
            value=getattr(cfg, "max_history_len", 30),
            key="cfg_max_history_len",
        )

    st.sidebar.divider()

    if st.sidebar.button("💾 設定を保存", use_container_width=True, type="primary"):
        save_settings()
        st.sidebar.success("✅ 設定を保存しました")
        st.rerun()

    if st.sidebar.button("🔄 デフォルトに戻す", use_container_width=True):
        reset_to_defaults()
        st.rerun()


def save_settings():
    """設定を保存"""
    pending_keys = [k for k in st.session_state.keys() if k.startswith("_pending_")]
    if not pending_keys:
        return

    try:
        from config.project_context import get_config, set_config

        cfg = get_config()
        updates = {}

        for key in pending_keys:
            model_key = key.replace("_pending_", "")
            updates[model_key] = st.session_state[key]
            del st.session_state[key]

        for key, value in updates.items():
            setattr(cfg, key, value)

        set_config(cfg)

        if hasattr(cfg, "_persist_to_toml"):
            cfg._persist_to_toml(cfg)

    except Exception as e:
        st.error(f"設定の保存に失敗: {e}")


def reset_to_defaults():
    """デフォルト設定にリセット"""
    default_cfg = GlobalConfigModel.default()
    try:
        from config.project_context import set_config
        set_config(default_cfg)
    except Exception:
        pass


def render_dashboard():
    """メ印第安ヤモンド"""
    st.title("📖 AutoNovel Dashboard")
    st.markdown("### AI小説執筆プラットフォーム")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📚 プロジェクト", "0", help="現在のプロジェクト数")
    with col2:
        st.metric("✍️ 執筆済み", "0文字", help="合計執筆文字数")
    with col3:
        st.metric("🤖 APIコスト", "¥0", help="今月のAPI使用コスト")
    with col4:
        st.metric("⚡ 処理状態", "待機中", help="現在の処理状態")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🚀 クイックスタート")
        st.markdown("""
        1. **プロット作成** - 物語の全体構成をAIが自動生成
        2. **詳細展開** - 各 章/エピソードの展開を詳細化
        3. **執筆開始** - AIが本文を自動執筆
        4. **品質チェック** - 論理的一貫性とカタルシス評価
        """)

        col_start, col_demo = st.columns(2)
        with col_start:
            if st.button("▶️ 新規プロジェクト作成", use_container_width=True, type="primary"):
                st.info("「プロット作成」ページから開始してください")
        with col_demo:
            if st.button("📖 デモ実行", use_container_width=True):
                st.info("デモ機能は準備中です")

    with col_right:
        st.subheader("⚙️ 現在の設定")
        cfg = load_config()

        st.markdown(f"""
        - **執筆モデル**: `{getattr(cfg, 'model_writing', 'N/A')}`
        - **コストモード**: `{getattr(cfg, 'cost_mode', 'balanced')}`
        - **NSFW許可**: {'✅' if getattr(cfg, 'enable_nsfw', False) else '❌'}
        - **自動バックアップ**: {'✅' if getattr(cfg, 'auto_backup', True) else '❌'}
        """)


def render_settings_tab():
    """設定タブ视图"""
    st.subheader("🎛️ 詳細設定")

    tab1, tab2, tab3, tab4 = st.tabs(["🤖 モデル", "🔧 機能", "🔒 安全", "💰 コスト"])

    with tab1:
        st.markdown("### LLMモデル設定")
        st.caption("各工程で使用するAIモデルを個別に設定できます")

        cfg = load_config()
        model_settings = [
            ("model_writing", "✍️ 執筆モデル", "物語の本文を執筆します", "gemma-4-31b-it"),
            ("model_planning", "📝 プロットモデル", "物語の全体構成を立案します", "gemini-3.5-flash-lite"),
            ("model_plot_expansion", "🔍 詳細展開モデル", "各 эпизод の詳細を展開します", "gemma-4-31b-it"),
            ("model_climax", "🔥 クライマックスモデル", "見せ場.Highlights を執筆します", "gemma-4-31b-it"),
            ("model_ultra_stable", "🛡️ 安定処理モデル", "エラー時にフォールバックとして使用", "gemini-3.5-flash-lite"),
        ]

        for key, label, help_text, default in model_settings:
            current = getattr(cfg, key, default) or default
            options = list(PRESET_MODELS)
            if current not in options:
                options.insert(0, current)

            st.selectbox(
                f"{label}",
                options=options,
                index=options.index(current) if current in options else 0,
                key=f"tab_{key}",
                help=f"{help_text} (デフォルト: {default})",
            )

    with tab2:
        st.markdown("### 機能开关")
        st.caption("各機能を有効/無効にできます")

        ConfigState.init_defaults()

        st.toggle(
            "📝 **ドラフトポリシング** - 執筆後に文章を自動校正・洗練",
            value=ConfigState.get("enable_draft_polish", True),
            key="tab_enable_draft_polish",
        )
        st.toggle(
            "🎭 **アクタークォリティ評価** - LLMに文章品質を評価させる",
            value=ConfigState.get("enable_actor_critic", True),
            key="tab_enable_actor_critic",
        )
        st.toggle(
            "🔍 **詳細オーディット** - 追加の品質チェックを実行",
            value=ConfigState.get("enable_heavy_audit", True),
            key="tab_enable_heavy_audit",
        )
        st.toggle(
            "⚡ **プリフェッチ** - 後続エピソードを事前に生成",
            value=getattr(load_config(), "prefetch_enabled", True),
            key="tab_prefetch_enabled",
        )
        st.toggle(
            "🔄 **コンテキストトリミング** - コンテキスト長超過時に自動トリミング",
            value=getattr(load_config(), "context_trimming_enabled", True),
            key="tab_context_trimming_enabled",
        )

    with tab3:
        st.markdown("### 安全・フィルタ設定")
        st.caption("コンテンツフィルタと安全設定を管理")

        cfg = load_config()

        st.toggle(
            "🔞 **NSFW/官能コンテンツ許可**",
            value=getattr(cfg, "enable_nsfw", False),
            key="tab_enable_nsfw",
            help="官能的な描写を含むコンテンツを許可します",
        )

        safety_level = st.selectbox(
            "🛡️ **セーフティレベル**",
            options=list(SAFETY_OPTIONS.keys()),
            format_func=lambda x: SAFETY_OPTIONS[x],
            index=list(SAFETY_OPTIONS.keys()).index(
                getattr(cfg, "safety_filter_level", "BLOCK_ONLY_HIGH") or "BLOCK_ONLY_HIGH"
            ),
            key="tab_safety_filter_level",
        )

        st.slider(
            "📊 **類似度閾値**",
            min_value=0.0,
            max_value=1.0,
            value=float(getattr(cfg, "similarity_threshold", 0.75)),
            step=0.05,
            key="tab_similarity_threshold",
            help="エッジ保全の類似度閾値",
        )

    with tab4:
        st.markdown("### コスト管理")
        st.caption("API使用コストを控制在"

        cfg = load_config()

        cost_mode = st.selectbox(
            "💰 **コストモード**",
            options=list(COST_MODE_OPTIONS.keys()),
            format_func=lambda x: COST_MODE_OPTIONS[x],
            index=list(COST_MODE_OPTIONS.keys()).index(
                getattr(cfg, "cost_mode", "balanced") or "balanced"
            ),
            key="tab_cost_mode",
        )

        st.markdown("**現在の設定の効果:**")
        if cost_mode == "quality":
            st.info("🧠 常に最高品質なモデルを使用。コストは高いが品質は最大。")
        elif cost_mode == "balanced":
            st.info("⚖️ 品質とコストのバランス取れた設定。標準的なにおすすめ。")
        else:
            st.info("💰 可能な限り軽量なモデルを使用。コスト重視。")

        st.divider()

        st.markdown("#### 📊 使用量目安")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("今月のコスト", "¥0", "¥0/月末")
        with col_b:
            st.metric("使用トークン", "0K", "+0K 先月比")
        with col_c:
            budget = getattr(cfg, "monthly_budget_limit", 0) or 0
            if budget > 0:
                st.metric("予算残り", f"¥{budget:.0f}", "¥0 使用済み")
            else:
                st.metric("予算残り", "∞", "無制限")


def main():
    ConfigState.init_defaults()
    render_sidebar_settings()
    render_dashboard()

    with st.expander("🎛️ 詳細設定を開く", expanded=False):
        render_settings_tab()


if __name__ == "__main__":
    main()
