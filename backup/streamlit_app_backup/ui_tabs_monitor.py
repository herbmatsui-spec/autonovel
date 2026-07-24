import streamlit as st

from src.engine_service import EngineService
from streamlit_app.state import UIStateStore

# APIコスト設定 (monitor.py より)
COST_INPUT_FLASH = 0.00000025
COST_OUTPUT_FLASH = 0.0000015

@st.fragment(run_every=30)
def render_monitor_tab(state, engine: EngineService, book_id: int):
    from streamlit_app.ui.icons import ICON_MONITOR, ICON_SETTINGS, ICON_WRITING
    st.header(f"{ICON_MONITOR} パイプライン進捗モニター")

    # データの取得
    # NOTE: EngineServiceに同期メソッドを追加するか、API経由で取得することを推奨
    try:
        # DB直接ではなくAPI経由での取得に統一（プロキシ経由）
        stats = engine.get_pipeline_stats_sync(book_id) # EngineService側に同期版を定義
    except Exception:
        stats = {"error": "データ取得失敗"}

    if "error" in stats:
        st.error(f"統計データの取得に失敗しました: {stats['error']}")
        return

    # 1. 主要指標 (Metrics)
    from streamlit_app.ui.icons import ICON_CHECK, ICON_CREDIT_CARD, ICON_PEN

    # コスト概算計算
    estimated_tokens = (stats['total_chars'] * 2) / 0.7 if stats['total_chars'] else 0
    estimated_cost_usd = (estimated_tokens * COST_INPUT_FLASH) + (estimated_tokens * COST_OUTPUT_FLASH)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.caption(f"{ICON_CHECK} プロット進捗")
            st.metric("完了率", f"{stats['completed_plots']}/{stats['total_plots']} 話")
    with col2:
        with st.container(border=True):
            st.caption(f"{ICON_PEN} 執筆量")
            st.metric("累計文字数", f"{stats['total_chars']:,} 字")
    with col3:
        with st.container(border=True):
            st.caption(f"{ICON_CREDIT_CARD} APIコスト概算")
            st.metric("推定費用", f"${estimated_cost_usd:.4f}")

    st.divider()

    # 2. 進捗バー
    # 目標話数の取得 (BookProxy から)
    book = engine.get_book(book_id)
    target_eps = book.target_eps if book else 0

    if target_eps > 0:
        progress_pct = min(1.0, stats['total_chapters'] / target_eps)
        st.subheader(f"{ICON_WRITING} 本文執筆進捗")
        st.progress(progress_pct)
        st.caption(f"目標 {target_eps} 話中 {stats['total_chapters']} 話完了 ({progress_pct*100:.1f}%)")
    else:
        st.warning("目標話数が設定されていないため、進捗バーを表示できません。")

    st.divider()

    from streamlit_app.ui.icons import ICON_BOOK
    # 4. 物語状態（Narrative State）の可視化と操作
    st.subheader(f"{ICON_BOOK} 物語の状態遷移")

    states_enum_map = {
        "DAILY": "日常",
        "INCIDENT": "事件発生",
        "CONFLICT": "葛藤",
        "PRE_CLIMAX": "前クライマックス",
        "CLIMAX": "クライマックス",
        "RESOLUTION": "解決"
    }
    states_keys = list(states_enum_map.keys())

    if "total_plots" in stats and stats["total_plots"] > 0:
        completion_rate = stats['completed_plots'] / stats['total_plots']
        current_state_idx = min(int(completion_rate * len(states_keys)), len(states_keys) - 1)

        cols = st.columns(len(states_keys))
        for i, s_key in enumerate(states_keys):
            with cols[i]:
                label = states_enum_map[s_key]
                if i == current_state_idx:
                    st.markdown(f"**{ICON_SUCCESS} {label}**")
                    st.caption("現在の推定状態")
                else:
                    st.markdown(f"⚪ {label}")
    else:
        st.info("物語の状態を判定するためのプロットデータが不足しています。")

    with st.expander(f"{ICON_SETTINGS} 物語制御 (デバッグ用)"):
        st.caption("物語の状態や遷移パスを強制的に変更します。次回のパイプライン実行時に反映されます。")

        col_state, col_path = st.columns(2)
        with col_state:
            target_state = st.selectbox("遷移先状態", states_keys, key="monitor_target_state")
        with col_path:
            target_path = st.selectbox("優先遷移パス", ["standard", "twist"], key="monitor_target_path")

        if st.button("設定を適用", use_container_width=True, key="monitor_apply_settings"):
            runtime_state = UIStateStore.get().runtime.global_state

            runtime_state['forced_narrative_state'] = target_state
            runtime_state['preferred_narrative_path'] = target_path

            st.toast(f"状態: {target_state}, パス: {target_path} に設定しました")

    # 官能曲線の可視化
    from streamlit_app.state import get_session
    session = get_session()
    if session.config.get("enable_nsfw", False):
        import plotly.graph_objects as go
        st.subheader("🌡️ 官能曲線 (Erotic Curve)")

        try:
            plots = engine.get_all_plots(book_id)
        except Exception:
            plots = []

        if plots:
            intensities = [getattr(p, 'erotic_intensity', 0) or 0 for p in plots]
            ep_nums = [p.ep_num for p in plots]

            if any(i > 0 for i in intensities):
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=ep_nums, y=intensities,
                    fill='tozeroy', mode='lines+markers',
                    line=dict(color='#7b1518', width=2),
                    fillcolor='rgba(123,21,24,0.3)',
                    name='官能強度'
                ))
                fig.update_layout(
                    xaxis_title="話数", yaxis_title="官能強度 (0-5)",
                    yaxis=dict(range=[0, 5.5]),
                    template="plotly_dark",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("官能描写はまだ設定・生成されていません。")
        else:
            st.info("プロット情報がありません。")

    st.divider()

    from streamlit_app.ui.icons import ICON_BOOK
    # 3. 最近の執筆履歴
    st.subheader(f"{ICON_BOOK} 最近の執筆ログ (最新5話)")
    recent = stats['recent_chapters']
    if not recent:
        st.info("まだ執筆された本文はありません。")
    else:
        # 表示用に整形
        history_data = []
        for chap in recent:
            ep_num, title, chars, created_at = chap
            history_data.append({
                "話数": f"第{ep_num:02d}話",
                "タイトル": title,
                "文字数": f"{chars:,}",
                "作成日時": created_at
            })
        st.table(history_data)

    # 自動更新ボタン (Streamlitの仕様上、完全自動はFragmentが必要だが、まずは手動リフレッシュを提供)
    from streamlit_app.ui.icons import ICON_RECYCLE
    if st.button(f"{ICON_RECYCLE} データを更新"):
        st.rerun() # Fragment内でのrerunはFragmentのみを更新する
