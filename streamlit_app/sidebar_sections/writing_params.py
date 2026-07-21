"""
streamlit_app/sidebar_sections/writing_params.py - 執筆パラメータ設定パネル
"""
from __future__ import annotations

import streamlit as st
from config.streamlit_adapter import StreamlitConfig as GlobalConfig
from streamlit_app.ui.components.nsfw_disclaimer import render_nsfw_disclaimer
from streamlit_app.ui_components import inject_focus_css
from streamlit_app.state import UIStateStore, SessionManager, get_session
from streamlit_app.ui.icons import ICON_SETTINGS, ICON_WRITING

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
DEFAULT_DESIRES = ["カタルシス"]

def render_sidebar_settings() -> None:
    """禁止表現設定や読者欲望設定など、執筆のパラメータ設定パネルを描画する。"""
    # 1. 執筆環境設定
    with st.container():
        if st.toggle(
            f"{ICON_WRITING} 集中執筆モード（明朝体）",
            value=False,
            help="背景をシンプルにし、文字を明朝体に変更して執筆に集中します。",
        ):
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
                    help="AIが生成時に避けるべき表現を指定します。",
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
                current_hook = (
                    UIStateStore.get_runtime().selected_emotional_hook or DEFAULT_DESIRES[0]
                )
                if current_hook not in HOOK_OPTIONS:
                    current_hook = HOOK_OPTIONS[0]
                hook = st.selectbox(
                    "🎯 感情起点（刺さり）",
                    HOOK_OPTIONS,
                    index=HOOK_OPTIONS.index(current_hook),
                    key="emotional_hook_select",
                    help="この話で読者に何を感じさせるかを1つ選択します。品質はこの感情に従属します。",
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
                    [
                        "カタルシス",
                        "ざまぁ",
                        "萌え",
                        "官能",
                        "独占欲",
                        "背徳感",
                        "恐怖",
                        "感動",
                        "笑い",
                        "謎解き",
                        "成り上がり",
                    ],
                    default=UIStateStore.get_runtime().selected_desires,
                    key="reader_desires_select",
                    help="ターゲット読者が作品に求める感情的な報酬を選択します。",
                )
                if desires != UIStateStore.get_runtime().selected_desires:
                    UIStateStore.get_runtime().selected_desires = desires
                    st.toast("❤️ 読者欲望設定を更新しました")

        render_reader_desires()

    # 詳細設定
    with st.expander(f"{ICON_SETTINGS} 高度な詳細設定", expanded=False):
        st.caption("⚠️ 設定の変更は生成されるコンテンツの傾向に大きく影響します。")
        session = get_session()
        nsfw_enabled = st.toggle(
            "🔞 NSFWモードを有効化",
            value=session.config.get("enable_nsfw", False),
            help="制限の厳しい表現や官能的な描写を許容するようAIに指示し、セーフティフィルターを緩和します。",
        )
        if nsfw_enabled != session.config.get("enable_nsfw"):
            if nsfw_enabled:
                if render_nsfw_disclaimer():
                    session.config["enable_nsfw"] = True
                    session.config["safety_filter_level"] = "BLOCK_NONE"
                    SessionManager.save_state(session)
                    st.toast("🔞 セーフティ設定を更新しました")
                    st.rerun()
                else:
                    st.rerun()
            else:
                session.config["enable_nsfw"] = False
                session.config["safety_filter_level"] = "BLOCK_ONLY_HIGH"
                session.config["erotic_intensity"] = 0
                SessionManager.save_state(session)
                st.toast("🛡️ セーフティ設定を元に戻しました")
                st.rerun()

        if session.config.get("enable_nsfw", False):
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
                index=preset_keys.index(
                    session.config.get("erotic_platform_preset", "kakuyomu_romance")
                )
                if session.config.get("erotic_platform_preset") in preset_keys
                else 0,
                format_func=lambda k: preset_labels[k],
                help="プラットフォームに応じて表現の上限が自動制御されます",
            )
            if selected_preset != session.config.get("erotic_platform_preset"):
                session.config["erotic_platform_preset"] = selected_preset
                SessionManager.save_state(session)

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
                    touch_w = st.slider("触覚", 0, 100, session.config.get("erotic_sensory_touch", 80))
                    scent_w = st.slider("嗅覚", 0, 100, session.config.get("erotic_sensory_scent", 60))
                with col2:
                    sound_w = st.slider("聴覚", 0, 100, session.config.get("erotic_sensory_sound", 70))
                    gaze_w = st.slider("視線", 0, 100, session.config.get("erotic_sensory_gaze", 50))
                with col3:
                    breath_w = st.slider("呼吸", 0, 100, session.config.get("erotic_sensory_breath", 75))
                    taste_w = st.slider("味覚", 0, 100, session.config.get("erotic_sensory_taste", 30))

                sensory_weights = {
                    "touch": touch_w, "scent": scent_w, "sound": sound_w,
                    "gaze": gaze_w, "breath": breath_w, "taste": taste_w,
                }
                if sensory_weights != session.config.get("erotic_sensory_weights"):
                    session.config["erotic_sensory_weights"] = sensory_weights
                    SessionManager.save_state(session)

                st.caption("⏱️ ペーシング比率")
                col4, col5, col6 = st.columns(3)
                with col4:
                    build_r = st.slider("溜め(Build)", 1, 10, session.config.get("erotic_pace_build", 3))
                with col5:
                    peak_r = st.slider("頂点(Peak)", 1, 10, session.config.get("erotic_pace_peak", 2))
                with col6:
                    afterglow_r = st.slider("余韻(Afterglow)", 1, 10, session.config.get("erotic_pace_afterglow", 2))

                pace_ratios = {"build": build_r, "peak": peak_r, "afterglow": afterglow_r}
                if pace_ratios != session.config.get("erotic_pace_ratios"):
                    session.config["erotic_pace_ratios"] = pace_ratios
                    SessionManager.save_state(session)

                st.caption("📝 品質パラメータ")
                metaphor_d = st.slider("比喩密度", 0, 100, session.config.get("erotic_metaphor_density", 50))
                psych_d = st.slider("心理描写深度", 0, 100, session.config.get("erotic_psychology_depth", 50))
                if metaphor_d != session.config.get("erotic_metaphor_density"):
                    session.config["erotic_metaphor_density"] = metaphor_d
                    SessionManager.save_state(session)
                if psych_d != session.config.get("erotic_psychology_depth"):
                    session.config["erotic_psychology_depth"] = psych_d
                    SessionManager.save_state(session)

                if st.button("🔄 エロ設定をリセット", use_container_width=True):
                    session.config["erotic_sensory_weights"] = None
                    session.config["erotic_pace_ratios"] = None
                    session.config["erotic_metaphor_density"] = 50
                    session.config["erotic_psychology_depth"] = 50
                    session.config["erotic_use_video_patterns"] = True
                    SessionManager.save_state(session)
                    st.rerun()

        GlobalConfig().display_sidebar()
