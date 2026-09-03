"""
streamlit_app/pages/00_Settings.py — 設定専用ページ

このファイルで全ての設定を一元管理できます。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit_app.state import ConfigState

st.set_page_config(
    page_title="AutoNovel - 設定",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ 設定")
st.markdown("---")

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


def load_config():
    try:
        from config.project_context import get_config
        return get_config()
    except Exception:
        from config.models import GlobalConfigModel
        return GlobalConfigModel.default()


def save_all_settings():
    """全設定を保存"""
    try:
        from config.project_context import get_config, set_config

        cfg = get_config()

        model_keys = [
            "model_writing", "model_planning", "model_plot_expansion",
            "model_climax", "model_ultra_stable", "model_stable_fallback", "model_embedding"
        ]
        for key in model_keys:
            widget_key = f"cfg_{key}"
            if widget_key in st.session_state:
                setattr(cfg, key, st.session_state[widget_key])

        cfg.openai_api_key = st.session_state.get("cfg_openai_api_key", cfg.openai_api_key)
        cfg.openai_base_url = st.session_state.get("cfg_openai_base_url", cfg.openai_base_url)

        cfg.enable_nsfw = st.session_state.get("cfg_enable_nsfw", cfg.enable_nsfw)
        cfg.safety_filter_level = st.session_state.get("cfg_safety_filter_level", cfg.safety_filter_level)
        cfg.similarity_threshold = st.session_state.get("cfg_similarity_threshold", cfg.similarity_threshold)
        cfg.min_immersion_score = st.session_state.get("cfg_min_immersion_score", cfg.min_immersion_score)

        cfg.cost_mode = st.session_state.get("cfg_cost_mode", cfg.cost_mode)
        cfg.auto_backup = st.session_state.get("cfg_auto_backup", cfg.auto_backup)
        cfg.max_history_len = st.session_state.get("cfg_max_history_len", cfg.max_history_len)

        cfg.enable_draft_polish = st.session_state.get("cfg_enable_draft_polish", cfg.enable_draft_polish)
        cfg.enable_actor_critic = st.session_state.get("cfg_enable_actor_critic", cfg.enable_actor_critic)
        cfg.enable_heavy_audit = st.session_state.get("cfg_enable_heavy_audit", cfg.enable_heavy_audit)
        cfg.prefetch_enabled = st.session_state.get("cfg_prefetch_enabled", cfg.prefetch_enabled)
        cfg.context_trimming_enabled = st.session_state.get("cfg_context_trimming_enabled", cfg.context_trimming_enabled)
        cfg.enable_semantic_edge_preservation = st.session_state.get("cfg_enable_semantic_edge_preservation", cfg.enable_semantic_edge_preservation)
        cfg.enable_dogfeeding = st.session_state.get("cfg_enable_dogfeeding", cfg.enable_dogfeeding)
        cfg.fail_fast_mode = st.session_state.get("cfg_fail_fast_mode", cfg.fail_fast_mode)
        cfg.specialized_amplifier_enabled = st.session_state.get("cfg_specialized_amplifier_enabled", cfg.specialized_amplifier_enabled)

        cfg.context_window_target_ratio = st.session_state.get("cfg_context_window_target_ratio", cfg.context_window_target_ratio)
        cfg.prefetch_episode_count = st.session_state.get("cfg_prefetch_episode_count", cfg.prefetch_episode_count)

        set_config(cfg)

        if hasattr(cfg, "_persist_to_toml"):
            cfg._persist_to_toml(cfg)

        st.success("✅ 設定を保存しました")
        return True
    except Exception as e:
        st.error(f"❌ 設定の保存に失敗: {e}")
        return False


def main():
    ConfigState.init_defaults()
    cfg = load_config()

    tab_models, tab_features, tab_safety, tab_costs, tab_advanced = st.tabs([
        "🤖 モデル設定",
        "🔧 機能开关",
        "🔒 安全・品質設定",
        "💰 コスト・保存",
        "🔬 詳細設定",
    ])

    with tab_models:
        st.subheader("🤖 LLMモデル設定")
        st.markdown("各工程で使用するAIモデルを個別に設定できます")

        with st.container(border=True):
            st.markdown("#### ✍️ 執筆設定")
            c1, c2 = st.columns(2)
            with c1:
                options = list(PRESET_MODELS)
                current = cfg.model_writing or "gemma-4-31b-it"
                if current not in options:
                    options.insert(0, current)
                st.selectbox(
                    "執筆モデル",
                    options=options,
                    index=options.index(current) if current in options else 0,
                    key="cfg_model_writing",
                    help="物語の本文を執筆する際に使用するモデル",
                )
            with c2:
                options = list(PRESET_MODELS)
                current = cfg.model_climax or "gemma-4-31b-it"
                if current not in options:
                    options.insert(0, current)
                st.selectbox(
                    "クライマックスモデル",
                    options=options,
                    index=options.index(current) if current in options else 0,
                    key="cfg_model_climax",
                    help="見せ場.Highlights を執筆する際に使用するモデル",
                )

        with st.container(border=True):
            st.markdown("#### 📝 プロット設定")
            c1, c2 = st.columns(2)
            with c1:
                options = list(PRESET_MODELS)
                current = cfg.model_planning or "gemini-3.5-flash-lite"
                if current not in options:
                    options.insert(0, current)
                st.selectbox(
                    "プロットモデル",
                    options=options,
                    index=options.index(current) if current in options else 0,
                    key="cfg_model_planning",
                    help="物語の全体構成を立案する際に使用するモデル",
                )
            with c2:
                options = list(PRESET_MODELS)
                current = cfg.model_plot_expansion or "gemma-4-31b-it"
                if current not in options:
                    options.insert(0, current)
                st.selectbox(
                    "詳細展開モデル",
                    options=options,
                    index=options.index(current) if current in options else 0,
                    key="cfg_model_plot_expansion",
                    help="各 эпизод の詳細を展開する際に使用するモデル",
                )

        with st.container(border=True):
            st.markdown("#### 🛡️ 安定性設定")
            c1, c2 = st.columns(2)
            with c1:
                options = list(PRESET_MODELS)
                current = cfg.model_ultra_stable or "gemini-3.5-flash-lite"
                if current not in options:
                    options.insert(0, current)
                st.selectbox(
                    "フォールバックモデル (ultra_stable)",
                    options=options,
                    index=options.index(current) if current in options else 0,
                    key="cfg_model_ultra_stable",
                    help="エラー時にフォールバックとして使用される安定指向のモデル",
                )
            with c2:
                options = list(PRESET_MODELS)
                current = getattr(cfg, "model_stable_fallback", "gemma-4-31b-it") or "gemma-4-31b-it"
                if current not in options:
                    options.insert(0, current)
                st.selectbox(
                    "安定フォールバックモデル",
                    options=options,
                    index=options.index(current) if current in options else 0,
                    key="cfg_model_stable_fallback",
                    help="エラー時の2段階目フォールバック（より安定重視）",
                )

        with st.container(border=True):
            st.markdown("#### 🔍 埋め込みモデル")
            options = list(PRESET_MODELS)
            current = getattr(cfg, "model_embedding", "text-embedding-004") or "text-embedding-004"
            if current not in options:
                options.insert(0, current)
            st.selectbox(
                "埋め込みモデル",
                options=options,
                index=options.index(current) if current in options else 0,
                key="cfg_model_embedding",
                help="ベクトル検索・類似度計算に使用する埋め込みモデル",
            )

        with st.container(border=True):
            st.markdown("#### 🔑 API設定")
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

    with tab_features:
        st.subheader("🔧 機能开关")
        st.markdown("各機能を有効/無効に切り替えできます")

        with st.container(border=True):
            st.markdown("#### ✏️ 執筆機能")
            st.toggle(
                "📝 ドラフトポリシング",
                value=getattr(cfg, "enable_draft_polish", True),
                key="cfg_enable_draft_polish",
                help="執筆後に文章を自動校正・洗練させる",
            )
            st.toggle(
                "🎭 アクタークォリティ評価",
                value=getattr(cfg, "enable_actor_critic", True),
                key="cfg_enable_actor_critic",
                help="LLMに文章の品質を評価させる",
            )
            st.toggle(
                "📖 スタイルRAG",
                value=True,
                key="cfg_style_rag_enabled",
                help="文脈に沿ったスタイルを維持する",
            )

        with st.container(border=True):
            st.markdown("#### 🔍 品質管理")
            st.toggle(
                "🔍 詳細オーディット",
                value=getattr(cfg, "enable_heavy_audit", True),
                key="cfg_enable_heavy_audit",
                help="追加の詳細品質チェックを実行",
            )
            st.toggle(
                "🎯 エッジ保全",
                value=getattr(cfg, "enable_semantic_edge_preservation", True),
                key="cfg_enable_semantic_edge_preservation",
                help="物語のエッジ（場面の繋ぎ目）を意味的に保全",
            )
            st.toggle(
                "🐕 ドッグフィーディング",
                value=getattr(cfg, "enable_dogfeeding", True),
                key="cfg_enable_dogfeeding",
                help="生成結果を次回学習にフィードバック（自己改善ループ）",
            )
            st.toggle(
                "🎯 専用アンプ",
                value=getattr(cfg, "specialized_amplifier_enabled", True),
                key="cfg_specialized_amplifier_enabled",
                help="特定ジャンル向けの増幅処理を有効化",
            )

        with st.container(border=True):
            st.markdown("#### ⚡ パフォーマンス")
            st.toggle(
                "⚡ プリフェッチ",
                value=getattr(cfg, "prefetch_enabled", True),
                key="cfg_prefetch_enabled",
                help="後続エピソードを事前に生成",
            )
            st.toggle(
                "🔄 コンテキストトリミング",
                value=getattr(cfg, "context_trimming_enabled", True),
                key="cfg_context_trimming_enabled",
                help="コンテキスト長超過時に自動トリミング",
            )

        with st.container(border=True):
            st.markdown("#### 🚨 実行制御")
            st.toggle(
                "⚡ フェイルファストモード",
                value=getattr(cfg, "fail_fast_mode", False),
                key="cfg_fail_fast_mode",
                help="エラー発生時に即座に停止（デバッグ用）",
            )

    with tab_safety:
        st.subheader("🔒 安全・品質設定")
        st.markdown("コンテンツフィルタと安全設定を管理")

        with st.container(border=True):
            st.markdown("#### 🔞 コンテンツ設定")
            st.toggle(
                "NSFW/官能コンテンツ許可",
                value=getattr(cfg, "enable_nsfw", False),
                key="cfg_enable_nsfw",
                help="官能的な描写を含むコンテンツを許可します",
            )

        with st.container(border=True):
            st.markdown("#### 🛡️ セーフティレベル")
            st.selectbox(
                "セーフティレベル",
                options=list(SAFETY_OPTIONS.keys()),
                format_func=lambda x: SAFETY_OPTIONS[x],
                index=list(SAFETY_OPTIONS.keys()).index(
                    getattr(cfg, "safety_filter_level", "BLOCK_ONLY_HIGH") or "BLOCK_ONLY_HIGH"
                ),
                key="cfg_safety_filter_level",
            )

        with st.container(border=True):
            st.markdown("#### 📊 類似度閾値")
            st.caption("エッジ保全で使用する類似度判定の閾値")
            st.slider(
                "類似度閾値",
                min_value=0.0,
                max_value=1.0,
                value=float(getattr(cfg, "similarity_threshold", 0.75)),
                step=0.05,
                key="cfg_similarity_threshold",
                help="この値以上の類似度は重複とみなされる",
            )

        with st.container(border=True):
            st.markdown("#### 🎯 品質閾値")
            st.caption("生成品質の最低ライン")
            st.slider(
                "最低没入スコア",
                min_value=0.0,
                max_value=100.0,
                value=float(getattr(cfg, "min_immersion_score", 0.0)),
                step=5.0,
                key="cfg_min_immersion_score",
                help="このスコア未満の生成はリトライ対象（0で無効）",
            )

    with tab_costs:
        st.subheader("💰 コスト・保存")
        st.markdown("API使用コストを制御")

        with st.container(border=True):
            st.markdown("#### 💰 コストモード")
            st.selectbox(
                "コストモード",
                options=list(COST_MODE_OPTIONS.keys()),
                format_func=lambda x: COST_MODE_OPTIONS[x],
                index=list(COST_MODE_OPTIONS.keys()).index(
                    getattr(cfg, "cost_mode", "balanced") or "balanced"
                ),
                key="cfg_cost_mode",
            )

            st.markdown("**現在の設定の効果:**")
            cost_mode = st.session_state.get("cfg_cost_mode", "balanced")
            if cost_mode == "quality":
                st.info("🧠 常に最高品質なモデルを使用。コストは高いが品質は最大。")
            elif cost_mode == "balanced":
                st.info("⚖️ 品質とコストのバランス取れた設定。標準的な用途におすすめ。")
            else:
                st.info("💰 可能な限り軽量なモデルを使用。コスト重視。")

        with st.container(border=True):
            st.markdown("#### 📊 使用量目安")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("今月のコスト", "¥0", "¥0/月末")
            with col2:
                st.metric("使用トークン", "0K", "+0K 先月比")
            with col3:
                st.metric("API呼び出し", "0回", "+0 先月比")

        with st.container(border=True):
            st.markdown("#### 📁 保存設定")
            st.toggle(
                "自動バックアップ",
                value=getattr(cfg, "auto_backup", True),
                key="cfg_auto_backup",
                help="データを更新する際に自動的にデータベースのバックアップを作成",
            )
            st.number_input(
                "履歴最大保持数",
                min_value=1,
                max_value=100,
                value=getattr(cfg, "max_history_len", 30),
                key="cfg_max_history_len",
                help="メモリやコンテキストとして保持するエピソード履歴の最大数",
            )

    with tab_advanced:
        st.subheader("🔬 詳細設定")
        st.markdown("上級者向けの詳細パラメータ（通常は変更不要）")
        st.caption("⚠️ これらの設定は動作に大きく影響します。理解した上で変更してください。")

        with st.container(border=True):
            st.markdown("#### 🧠 コンテキストウィンドウ最適化")
            st.caption("LLMコンテキスト使用率の目標値とプリフェッチ設定")

            col1, col2 = st.columns(2)
            with col1:
                st.slider(
                    "目標使用率",
                    min_value=0.5,
                    max_value=0.95,
                    value=float(getattr(cfg, "context_window_target_ratio", 0.85)),
                    step=0.05,
                    key="cfg_context_window_target_ratio",
                    help="コンテキストウィンドウの目標使用率（高いほど多くの履歴を保持、低いほど余裕を持たせる）",
                )
            with col2:
                st.number_input(
                    "プリフェッチ エピソード数",
                    min_value=0,
                    max_value=10,
                    value=int(getattr(cfg, "prefetch_episode_count", 3)),
                    key="cfg_prefetch_episode_count",
                    help="事前に生成しておく後続エピソード数（0で無効）",
                )

            st.caption(f"最小予約トークン数: {getattr(cfg, 'context_window_min_reserve', 2000)} （環境変数 KAKU_CONTEXT_WINDOW_MIN_RESERVE で変更）")

    st.markdown("---")

    col_save, col_reset, col_export = st.columns([2, 1, 1])

    with col_save:
        if st.button("💾 設定を保存", use_container_width=True, type="primary"):
            save_all_settings()

    with col_reset:
        if st.button("🔄 デフォルトに戻す", use_container_width=True):
            try:
                from config.models import GlobalConfigModel
                from config.project_context import set_config
                set_config(GlobalConfigModel.default())
                st.success("デフォルト設定に戻しました")
                st.rerun()
            except Exception as e:
                st.error(f"エラー: {e}")

    with col_export:
        if st.button("📤 設定をエクスポート", use_container_width=True):
            st.info("設定のエクスポート機能は準備中です")


if __name__ == "__main__":
    main()
