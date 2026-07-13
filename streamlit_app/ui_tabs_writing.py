from typing import Any, Dict

import streamlit as st

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from streamlit_app.controllers.manager import UIControllerManager
from streamlit_app.event_bus import UIEventType
from streamlit_app.proxy import UltimateHegemonyEngineProxy as UltimateHegemonyEngine
from streamlit_app.ui_utils import trigger_app_rerun


@st.fragment
def render_plot_tab(state: Dict[str, Any], engine: UltimateHegemonyEngine, book_id: int) -> None:
    from streamlit_app.ui.components.widgets import render_primary_button, render_section_header
    from streamlit_app.ui.icons import ICON_PLANNING, ICON_SUCCESS

    render_section_header("ステップ2: プロット管理・生成", "物語の設計図を構築し、各話の構成を詳細化します", ICON_PLANNING)

    plots = engine.repo.get_all_plots(book_id)
    if not plots:
        st.info("プロットがありません。企画タブから作品を生成してください。")
        return

    st.markdown(f"#### 📊 プロット進捗状況 ({len(plots)}話)")

    # 進捗サマリーの表示 (メトリクス)
    completed_count = sum(1 for p in plots if p.status == "completed")
    draft_count = sum(1 for p in plots if not p.status == "completed" and p.detailed_blueprint)

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("完了", f"{completed_count}/{len(plots)}")
    m_col2.metric("設計済", f"{completed_count + draft_count}/{len(plots)}")
    m_col3.metric("進捗率", f"{(completed_count / len(plots) * 100):.1f}%")

    # 尖り保全ダッシュボード
    st.markdown("#### 🛡️ 尖り保全状況")
    for p in plots:
        status_val = getattr(p, 'quality_polish_status', None) or "pending"
        if status_val == "rejected_edge_loss":
            st.error(f"第{p.ep_num}話: ⚠️ 品質磨き上げで角が削られました（没戻し推奨）")
        elif status_val == "passed":
            st.success(f"第{p.ep_num}話: ✅ 尖り保全済み")
        else:
            st.caption(f"第{p.ep_num}話: 未検証")

    st.markdown("---")

    # 面白さ検証スコア表示
    st.markdown("#### 🎯 面白さ検証スコア")
    try:
        logs = engine.repo.get_entertainment_check_logs_by_book(book_id)
    except Exception:
        logs = []
    if logs:
        ep_nums = [log["ep_num"] for log in logs]
        scores = [log["interest_score"] for log in logs]
        if HAS_PLOTLY:
            fig = go.Figure(data=[go.Scatter(x=ep_nums, y=scores, mode="lines+markers", name="interest_score")])
            fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="閾値(60)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.line_chart(dict(zip(ep_nums, scores)))
        for log in logs:
            color = "🔴" if log["interest_score"] < 60 else "🟢"
            st.caption(f"第{log['ep_num']}話: {color} {log['interest_score']}点 ({log['physiological_reaction']})")
    else:
        st.caption("面白さ検証ログがありません。")

    st.markdown("---")

    # プロット詳細の表示
    for p in plots:
        status_icon = ICON_SUCCESS if p.status == "completed" else "📝" if (p.detailed_blueprint and len(p.detailed_blueprint) > 50) else "⬜"
        # ステータスに応じた色付けやラベルを検討
        status_label = "【完了】" if p.status == "completed" else "【設計済】" if p.detailed_blueprint else "【未着手】"

        with st.expander(f"{status_icon} {status_label} 第{p.ep_num}話: {p.title or '(未タイトル)'}"):
            if p.detailed_blueprint:
                col_bp, col_sc = st.columns(2)
                with col_bp:
                    with st.container(border=True):
                        st.markdown("**📜 設計図 (Blueprint)**")
                        st.write(p.detailed_blueprint)
                with col_sc:
                    if p.script_content:
                        with st.container(border=True):
                            st.markdown("**🎬 台本案 (Script)**")
                            st.write(p.script_content[:800] + "...")
                    else:
                        st.info("台本案はまだ生成されていません。")
            else:
                st.caption("設計図がまだ生成されていません。")

    st.markdown("---")
    if render_primary_button("🔄 プロットを一括更新/追加生成", key="gen_plots_all", icon="🔄"):
        params = {"book_id": book_id, "gen_from": 1, "gen_to": len(plots)}
        UIControllerManager(engine).emit(UIEventType.REQUEST_GENERATE_PLOT, params)
        trigger_app_rerun()

@st.fragment
def render_episode_list(state: Dict[str, Any], engine: UltimateHegemonyEngine, book_id: int) -> None:
    """Render the episode list UI fragment."""
    from streamlit_app.ui.components.widgets import render_secondary_button
    from streamlit_app.ui.icons import ICON_DOWNLOAD, ICON_FILE, ICON_TRASH, ICON_WARNING

    st.markdown("#### 📚 執筆済みエピソード")
    chapters = engine.repo.get_all_non_anchor_chapters(book_id)
    if not chapters:
        st.info("まだ本文が執筆されていません。")
    else:
        # 執筆状況のクイックサマリー
        total_chars = sum(len(ch.content or '') for ch in chapters)
        st.markdown(f"📝 **総執筆文字数:** `{total_chars:,}` 文字 / **完了話数:** `{len(chapters)}` 話")

        for ch in chapters:
            audit_note = ch.ai_insight or ""
            title_prefix = ICON_WARNING if "Audit" in audit_note else ICON_FILE

            # 監査警告がある場合は枠線で強調
            with st.expander(f"{title_prefix} 第{ch.ep_num}話: {ch.title} ({len(ch.content or '')}文字)"):
                if audit_note:
                    with st.container(border=True):
                        st.markdown(f"**🤖 AI監査フィードバック:**\n\n{audit_note}")

                if hasattr(ch, 'killer_phrase') and ch.killer_phrase:
                    st.markdown(f"**✨ 決め台詞:** `{ch.killer_phrase}`")

                st.text_area("本文", ch.content, height=300, key=f"view_ch_{ch.ep_num}")

                c_btn1, c_btn2 = st.columns([1, 1])
                with c_btn1:
                    st.download_button(f"{ICON_DOWNLOAD} ダウンロード", ch.content, file_name=f"ep{ch.ep_num}.txt", key=f"dl_{ch.ep_num}", use_container_width=True)
                with c_btn2:
                    if render_secondary_button(f"{ICON_TRASH} 削除", key=f"del_{ch.ep_num}", icon=""):
                        engine.repo.delete_chapter(book_id, ch.ep_num)
                        trigger_app_rerun()

@st.fragment
def render_import_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_WRITING
    st.header(f"{ICON_WRITING} 本文インポート（手書き原稿の取り込み）")
    plots = engine.repo.get_all_plots(book_id)
    ep_num = st.selectbox("対象話数", [p.ep_num for p in plots], format_func=lambda x: f"第{x}話")
    text = st.text_area("インポートする本文", height=400)
    do_refine = st.checkbox("商用クオリティ研磨を適用して保存", value=True)

    if st.button("📥 インポートして解析実行", type="primary"):
        if text:
            with st.spinner("AIが原稿を解析中..."):
                params = {"book_id": book_id, "ep_num": ep_num, "text": text, "do_refine": do_refine}
                UIControllerManager(engine).emit(UIEventType.REQUEST_IMPORT_CHAPTER, params)
                trigger_app_rerun()

@st.fragment
def render_writing_tab(state: Dict[str, Any], engine: UltimateHegemonyEngine, book_id: int) -> None:
    from streamlit_app.ui.components.widgets import render_section_header
    from streamlit_app.ui.icons import ICON_WRITING

    render_section_header("ステップ3: 本文執筆", "プロットに基づき、最高密度の本文を生成します", ICON_WRITING)

    plots = engine.repo.get_all_plots(book_id)
    if not plots:
        st.info("プロットが生成されていません。")
        return

    with st.container(border=True):
        st.markdown("#### ⚙️ 執筆パラメータ")
        col1, col2, col3, col4 = st.columns(4)
    with col1:
        write_from = st.number_input("開始話数", 1, value=1)
    with col2:
        write_to = st.number_input("終了話数", write_from, max_value=len(plots), value=min(int(write_from)+4, len(plots)))
    with col3:
        word_count = st.number_input("目標文字数", 500, 10000, 2500, 500)
    with col4:
        passion = st.slider("情熱 (Passion)", 0.0, 1.0, 0.5)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        do_refine = st.checkbox("💎 描写を高解像度化（文字数増量）", value=True, help="既存の文章を削らず、五感や心理描写を強化して厚みを持たせます。")
        pipeline_mode = st.checkbox("⚡ パイプラインモード (高速)", value=True)
    with col_c2:
        env = {
            "season": st.selectbox("季節背景", ["春","夏","秋","冬"]),
            "weather": st.selectbox("天候背景", ["晴天","雨","雪","嵐"])
        }

    from streamlit_app.ui.icons import ICON_PENCIL
    if st.button(f"{ICON_PENCIL} 執筆開始", type="primary"):
        params = {
            "book_id": book_id, "write_from": write_from, "write_to": write_to,
            "passion": passion, "word_count": word_count, "do_refine": do_refine,
            "env_state": env, "pipeline_mode": pipeline_mode
        }
        UIControllerManager(engine).emit(UIEventType.REQUEST_WRITE_EPISODES, params)
        trigger_app_rerun()

    st.divider()
    render_episode_list(state, engine, book_id)

def render_rebuild_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_PLANNING
    st.header(f"{ICON_PLANNING} プロット再構築（連載延長・テコ入れ）")
    st.info("過去の展開を引き継ぎつつ、ここから先の物語を再設計します。")

    plots = engine.repo.get_all_plots(book_id)
    max_ep = max([p.ep_num for p in plots], default=0)

    col1, col2 = st.columns(2)
    with col1:
        start_ep = st.number_input("再構築を開始する話数", 1, max_ep + 1, max_ep + 1)
        new_total = st.number_input("新しい最終話数", start_ep, 200, start_ep + 20)
    with col2:
        new_keywords = st.text_input("追加キーワード", "新展開, 新ライバル")
        trend_memo = st.text_area("追加したい要素", "読者の予想を裏切る展開を追加したい")

    col3, col4 = st.columns(2)
    with col3:
        cheat_scale = st.slider("チート強度", 0, 5, 4)
        cost_severity = st.slider("能力の代償", 0, 5, 2)
    with col4:
        system_assist = st.slider("システム補助率 (%)", 0, 100, 70)
        plot_pattern = st.selectbox("物語の型", ["exile_rise", "reincarnation_cheat", "slow_life"])

    from streamlit_app.ui.icons import ICON_HAMMER
    if st.button(f"{ICON_HAMMER} プロット再構築を予約実行", type="primary", use_container_width=True):
        params = {
            "book_id": book_id, "start_ep": start_ep, "new_total": new_total,
            "new_keywords": new_keywords, "trend_memo": trend_memo,
            "plot_pattern": plot_pattern, "cheat_scale": cheat_scale,
            "cost_severity": cost_severity, "system_assist": system_assist
        }
        UIControllerManager(engine).emit(UIEventType.REQUEST_REBUILD_PLOT, params)
        trigger_app_rerun()
