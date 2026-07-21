"""
sidebar.py - アプリケーションのサイドバー描画および作品管理UI
"""
from __future__ import annotations

import asyncio

import streamlit as st

from config.streamlit_adapter import StreamlitConfig as GlobalConfig
from src.engine_service import EngineService
from streamlit_app.health_check import validate_api_key_async
from streamlit_app.state import SessionManager, UIStateStore, get_session
from streamlit_app.ui.components.nsfw_disclaimer import render_nsfw_disclaimer
from streamlit_app.ui_components import inject_focus_css
from streamlit_app.utils import TokenUsageTracker

STRESS_THRESHOLD_HIGH = 65
STRESS_THRESHOLD_MEDIUM = 40
DEFAULT_APP_MODE = "easy"
DEFAULT_DESIRES = ["カタルシス"]

HOOK_OPTIONS = [
    "カタルシス",
    "共感の最深",
    "背筋の寒さ",
    "義憤",
    " Triumph ",
    "静寂の喜び",
    "郷愁",
    "畏敬",
]

def render_api_key_section(session) -> tuple[str | None, bool]:
    """APIキー入力セクションの描画とキー検証を行う。"""
    is_key_valid = UIStateStore.get_runtime().is_api_key_valid
    api_key_input = UIStateStore.get_api_key_input()

    if api_key_input is None and session.api_key:
        UIStateStore.set_api_key_input(session.api_key)
        api_key_input = session.api_key

    from streamlit_app.ui.icons import ICON_SETTINGS
    api_key = st.text_input(
        f"{ICON_SETTINGS} Gemini API Key",
        type="password",
        value=api_key_input or "",
        key="api_key_input",
        help="Google AI Studio (aistudio.google.com) で取得したAPIキーを入力してください。"
    )

    # プロバイダ選択
    from streamlit_app.state import UIStateStore
    current_provider = UIStateStore.get_runtime().llm_provider
    provider_options = ["gemini", "openai"]
    selected_provider = st.selectbox(
        "LLM Provider",
        provider_options,
        index=provider_options.index(current_provider) if current_provider in provider_options else 0,
        help="Gemini (Google) or OpenAI"
    )
    UIStateStore.get_runtime().llm_provider = selected_provider

    # 入力値が変わったら再検証
    if api_key != api_key_input:
        UIStateStore.set_api_key_input(api_key)
        UIStateStore.get_runtime().is_api_key_valid = False
        is_key_valid = False

    if st.button("🔑 キーを確定して開始", type="primary", use_container_width=True):
        if api_key:
            with st.spinner("APIキーを検証中..."):
                try:
                    is_valid = asyncio.run(validate_api_key_async(api_key))
                    UIStateStore.get_runtime().is_api_key_valid = is_valid
                    if is_valid:
                        session.api_key = api_key
                        SessionManager.save_state(session)
                        UIStateStore.get_runtime().app_mode = DEFAULT_APP_MODE
                        st.success("APIキーが確定されました。")
                        st.rerun()
                    else:
                        st.error("無効なAPIキーです。")
                except Exception as e:
                    st.error(f"検証エラー: {e}")
        else:
            st.warning("APIキーを入力してください。")

    if not api_key and session.api_key:
        # キーがクリアされた場合
        session.api_key = None
        UIStateStore.get_runtime().is_api_key_valid = False
        is_key_valid = False
        SessionManager.save_state(session)
        st.rerun()

    return session.api_key, is_key_valid


def render_mode_selector() -> None:
    """アプリの動作モード（かんたん/上級者）選択ラジオボタンを描画する。"""
    from streamlit_app.ui.icons import ICON_PLANNING, ICON_SETTINGS

    # モードごとの説明文
    mode_descriptions = {
        "easy": "AIプロデューサーのガイドに従って、対話形式でサクッと物語を構築します。初心者の方や、アイデアを素早く形にしたい方に最適です。",
        "advanced": "プロットの構造や詳細設定を自在にコントロールし、こだわり抜いた設計を行います。物語の構成に精通した方や、緻密な設計を好む方に最適です。"
    }

    mode_labels = {"easy": f"{ICON_PLANNING} かんたんモード", "advanced": f"{ICON_SETTINGS} 上級者モード"}
    current_mode = UIStateStore.get_runtime().app_mode

    # ラジオボタンによるモード選択
    new_mode = st.radio(
        "あなたに合ったスタイルを選択してください",
        list(mode_labels.keys()),
        index=list(mode_labels.keys()).index(current_mode) if current_mode in mode_labels else 0,
        format_func=lambda k: mode_labels[k],
    )

    # 選択中のモードに合わせて説明文を表示
    st.info(mode_descriptions.get(new_mode, ""))

    if new_mode != current_mode:
        UIStateStore.get_runtime().app_mode = new_mode
        st.rerun()


def render_sidebar_settings() -> None:
    """禁止表現設定や読者欲望設定など、執筆のパラメータ設定パネルを描画する。"""
    from streamlit_app.ui.icons import ICON_SETTINGS, ICON_WRITING

    # 1. 執筆環境設定
    with st.container():
        if st.toggle(f"{ICON_WRITING} 集中執筆モード（明朝体）", value=False, help="背景をシンプルにし、文字を明朝体に変更して執筆に集中します。"):
            inject_focus_css()

    st.divider()

    # 2. コンテンツ制御（禁止表現・欲望）
    with st.expander("🛠️ コンテンツ制御設定", expanded=False):
        @st.fragment
        def render_forbidden_patterns():
            with st.container():
                forbidden_input = st.text_area(
                    "🚫 禁止表現（1行1つ）",
                    value="\n".join(UIStateStore.get_runtime().forbidden_patterns),
                    height=80,
                    key="forbidden_patterns_input",
                    help="AIが生成時に避けるべき表現を指定します。"
                )
                patterns = [line.strip() for line in forbidden_input.split("\n") if line.strip()]
                if patterns != UIStateStore.get_runtime().forbidden_patterns:
                    UIStateStore.get_runtime().forbidden_patterns = patterns
                    st.toast("🚫 禁止表現を更新しました")

        render_forbidden_patterns()

        st.divider()

        @st.fragment
        def render_emotional_hook():
            with st.container():
                current_hook = UIStateStore.get_runtime().selected_emotional_hook or DEFAULT_DESIRES[0]
                if current_hook not in HOOK_OPTIONS:
                    current_hook = HOOK_OPTIONS[0]
                hook = st.selectbox(
                    "🎯 感情起点（刺さり）",
                    HOOK_OPTIONS,
                    index=HOOK_OPTIONS.index(current_hook),
                    key="emotional_hook_select",
                    help="この話で読者に何を感じさせるかを1つ選択します。品質はこの感情に従属します。"
                )
                if hook != UIStateStore.get_runtime().selected_emotional_hook:
                    UIStateStore.get_runtime().selected_emotional_hook = hook
                    st.toast("🎯 感情起点を更新しました")

        render_emotional_hook()

        st.divider()

        @st.fragment
        def render_reader_desires():
            with st.container():
                desires = st.multiselect(
                    "❤️ 読者欲望設定",
                    ["カタルシス", "ざまぁ", "萌え", "官能", "独占欲", "背徳感", "恐怖", "感動", "笑い", "謎解き", "成り上がり"],
                    default=UIStateStore.get_runtime().selected_desires,
                    key="reader_desires_select",
                    help="ターゲット読者が作品に求める感情的な報酬を選択します。"
                )
                if desires != UIStateStore.get_runtime().selected_desires:
                    UIStateStore.get_runtime().selected_desires = desires
                    st.toast("❤️ 読者欲望設定を更新しました")

        render_reader_desires()


    # 詳細設定
    with st.expander(f"{ICON_SETTINGS} 高度な詳細設定", expanded=False):
        st.caption("⚠️ 設定の変更は生成されるコンテンツの傾向に大きく影響します。")
        # NSFWモードのトグル
        session = get_session()
        nsfw_enabled = st.toggle("🔞 NSFWモードを有効化",
                                  value=session.config.get("enable_nsfw", False),
                                  help="制限の厳しい表現や官能的な描写を許容するようAIに指示し、セーフティフィルターを緩和します。")
        if nsfw_enabled != session.config.get("enable_nsfw"):
            if nsfw_enabled:
                # 同意確認モーダルを表示し、同意が得られた場合のみ有効化
                if render_nsfw_disclaimer():
                    session.config["enable_nsfw"] = True
                    session.config["safety_filter_level"] = "BLOCK_NONE"
                    SessionManager.save_state(session)
                    st.toast("🔞 セーフティ設定を更新しました")
                    st.rerun()
                else:
                    # 同意が得られなかった場合はトグルを戻す（再描画で反映）
                    st.rerun()
            else:
                session.config["enable_nsfw"] = False
                session.config["safety_filter_level"] = "BLOCK_ONLY_HIGH"
                session.config["erotic_intensity"] = 0
                SessionManager.save_state(session)
                st.toast("🛡️ セーフティ設定を元に戻しました")
                st.rerun()

        # テーマカラー切替
        if session.config.get("enable_nsfw", False):
            """, unsafe_allow_html=True)

            # 強度スライダーとプラットフォームプリセット選択
            from config.constants import EROTIC_INTENSITY_SCALE
            erotic_intensity = st.slider(
                "🌡️ 官能描写の強度",
                min_value=0,
                max_value=5,
                value=session.config.get("erotic_intensity", 2),
                format="%d",
                help="0:ほのぼの 〜 5:過激",
            )
            st.caption(f"現在の強度: {EROTIC_INTENSITY_SCALE.get(erotic_intensity, '不明')}")
            if erotic_intensity != session.config.get("erotic_intensity"):
                session.config["erotic_intensity"] = erotic_intensity
                SessionManager.save_state(session)

            from config.erotic_platform_presets import PLATFORM_PRESETS, get_preset_names
            preset_keys = get_preset_names()
            preset_labels = {k: PLATFORM_PRESETS[k]["name"] for k in preset_keys}
            selected_preset = st.selectbox(
                "📱 出力プラットフォーム",
                preset_keys,
                index=preset_keys.index(session.config.get("erotic_platform_preset", "kakuyomu_romance")) if session.config.get("erotic_platform_preset") in preset_keys else 0,
                format_func=lambda k: preset_labels[k],
                help="プラットフォームに応じて表現の上限が自動制御されます",
            )
            if selected_preset != session.config.get("erotic_platform_preset"):
                session.config["erotic_platform_preset"] = selected_preset
                SessionManager.save_state(session)

            # 詳細エロエージェント設定
            with st.expander("🎬 官能エージェント詳細設定", expanded=False):
                st.caption("詳細なパラメータ調整（上級者向け）")

                use_video_patterns = st.checkbox(
                    "映像パターン技術を有効にする",
                    value=session.config.get("erotic_use_video_patterns", True),
                    help="Fanza等の動画を参考にした文学技法の適用",
                )
                if use_video_patterns != session.config.get("erotic_use_video_patterns"):
                    session.config["erotic_use_video_patterns"] = use_video_patterns
                    SessionManager.save_state(session)

                st.caption("🎯 感覚ウェイト調整")
                col1, col2, col3 = st.columns(3)
                with col1:
                    touch_w = st.slider(
                        "触覚", 0, 100,
                        session.config.get("erotic_sensory_touch", 80),
                        help="触れ屋の重視度"
                    )
                    scent_w = st.slider(
                        "嗅覚", 0, 100,
                        session.config.get("erotic_sensory_scent", 60),
                        help="匂いの重視度"
                    )
                with col2:
                    sound_w = st.slider(
                        "聴覚", 0, 100,
                        session.config.get("erotic_sensory_sound", 70),
                        help="音・喘ぎの重視度"
                    )
                    gaze_w = st.slider(
                        "視線", 0, 100,
                        session.config.get("erotic_sensory_gaze", 50),
                        help="見つめることの重視度"
                    )
                with col3:
                    breath_w = st.slider(
                        "呼吸", 0, 100,
                        session.config.get("erotic_sensory_breath", 75),
                        help="息遣いの重視度"
                    )
                    taste_w = st.slider(
                        "味覚", 0, 100,
                        session.config.get("erotic_sensory_taste", 30),
                        help="唇・口の中の感覚の重視度"
                    )

                sensory_weights = {
                    "touch": touch_w,
                    "scent": scent_w,
                    "sound": sound_w,
                    "gaze": gaze_w,
                    "breath": breath_w,
                    "taste": taste_w,
                }
                if sensory_weights != session.config.get("erotic_sensory_weights"):
                    session.config["erotic_sensory_weights"] = sensory_weights
                    SessionManager.save_state(session)

                st.caption("⏱️ ペーシング比率")
                col4, col5, col6 = st.columns(3)
                with col4:
                    build_r = st.slider(
                        "溜め(Build)", 1, 10,
                        session.config.get("erotic_pace_build", 3),
                        help="溜めフェーズの詳細度"
                    )
                with col5:
                    peak_r = st.slider(
                        "頂点(Peak)", 1, 10,
                        session.config.get("erotic_pace_peak", 2),
                        help="ピークフェーズの質"
                    )
                with col6:
                    afterglow_r = st.slider(
                        "余韻(Afterglow)", 1, 10,
                        session.config.get("erotic_pace_afterglow", 2),
                        help="事後描写の分量"
                    )

                pace_ratios = {"build": build_r, "peak": peak_r, "afterglow": afterglow_r}
                if pace_ratios != session.config.get("erotic_pace_ratios"):
                    session.config["erotic_pace_ratios"] = pace_ratios
                    SessionManager.save_state(session)

                st.caption("📝 品質パラメータ")
                metaphor_d = st.slider(
                    "比喩密度", 0, 100,
                    session.config.get("erotic_metaphor_density", 50),
                    help="比喩表現の使用頻度"
                )
                psych_d = st.slider(
                    "心理描写深度", 0, 100,
                    session.config.get("erotic_psychology_depth", 50),
                    help="心理描写の細かさ"
                )
                if metaphor_d != session.config.get("erotic_metaphor_density"):
                    session.config["erotic_metaphor_density"] = metaphor_d
                    SessionManager.save_state(session)
                if psych_d != session.config.get("erotic_psychology_depth"):
                    session.config["erotic_psychology_depth"] = psych_d
                    SessionManager.save_state(session)

                # リセットボタン
                if st.button("🔄 エロ設定をリセット", use_container_width=True):
                    session.config["erotic_sensory_weights"] = None
                    session.config["erotic_pace_ratios"] = None
                    session.config["erotic_metaphor_density"] = 50
                    session.config["erotic_psychology_depth"] = 50
                    session.config["erotic_use_video_patterns"] = True
                    SessionManager.save_state(session)
                    st.rerun()

        GlobalConfig().display_sidebar()


def render_token_usage() -> None:
    """トークン使用量と想定されるコストの表示。"""
    stats = UIStateStore.get_runtime().token_stats
    tracker = TokenUsageTracker(stats.model_dump() if hasattr(stats, "model_dump") else stats)
    st.metric("API呼び出し回数", f"{stats.calls}回")
    st.metric("推定コスト",      f"${tracker.get_cost_usd():.4f}")


def render_sidebar(engine_ready: bool = False) -> str | None:
    # 再描画回数の計測
    UIStateStore.increment_rerun_count()

    with st.sidebar:
        st.caption(f"🔄 Full Rerun Count: {UIStateStore.get_rerun_count()}")
        st.title("⚔️ 覇権小説エンジン v3.0")
        st.caption("カクヨムランキング1位を狙う全自動執筆ツール")

    session = get_session()

    st.markdown("### ⚙️ システム設定")
    api_key, is_key_valid = render_api_key_section(session)

    if not api_key or not is_key_valid:
        st.warning("有効なAPIキーを入力し、確定ボタンを押してください。")
        return None

    st.divider()

    st.markdown("### 🎮 操作モード")
    render_mode_selector()

    st.divider()

    st.markdown("### 🛠️ 執筆パラメータ")
    render_sidebar_settings()

    st.divider()

    st.markdown("### 💰 リソース状況")
    render_token_usage()

    return api_key


def render_book_selector(service: EngineService) -> int | None:
    """作品選択ボックスをサイドバーに描画し、選択中の作品IDを管理する。"""
    books = service.get_all_books()

    with st.sidebar:
        st.markdown("### 📚 作品管理")
        if not books:
            st.info("まだ作品がありません。企画タブから新しい作品を生成してください。")
            return None

        book_ids = [b.id for b in books]
        book_opts = {b.id: f"[{b.id}] {b.title}" for b in books}

        # 型安全なセッションからIDを取得
        session = get_session()
        current_id = session.current_book_id
        default_idx = 0
        if current_id in book_ids:
            default_idx = book_ids.index(current_id)

        selected = st.selectbox(
            "執筆する作品を選択してください",
            book_ids,
            index=default_idx,
            format_func=lambda x: book_opts[x],
            key="sidebar_book_selector",
            help="現在編集・分析したい作品を切り替えます。"
        )
        session.current_book_id = selected

        detail = service.get_book_details(selected)
        if detail:
            book_detail = detail["book"]
            stress = detail["stress"]
            stress_icon = "🔴" if stress >= STRESS_THRESHOLD_HIGH else "🟡" if stress >= STRESS_THRESHOLD_MEDIUM else "🟢"
            st.caption(f"ジャンル: {book_detail.genre}")
            st.caption(f"目標話数: {book_detail.target_eps}話")
            st.caption(f"{stress_icon} 累積ストレス: {stress}/100")

        if st.button("🗑️ 作品を削除", type="secondary", use_container_width=True):
            service.delete_book(selected)
            if session.current_book_id == selected:
                UIStateStore.update(lambda s: setattr(s, "current_book_id", None), notify_keys=["current_book_id"])
            st.rerun()

        return selected
