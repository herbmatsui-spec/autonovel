import streamlit as st
from engine import UltimateHegemonyEngine, safe_run_async
from engine_service import HegemonyService
from background import run_in_background

def render_plot_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    st.header("📖 ステップ2: プロット管理・生成")
    plots = safe_run_async(engine.repo.get_all_plots(book_id))
    if not plots:
        st.info("プロットがありません。企画タブから作品を生成してください。")
        return

    st.subheader(f"全{len(plots)}話のプロット状況")
    for p in plots:
        status_icon = "✅" if p.status == "completed" else "📝" if (p.detailed_blueprint and len(p.detailed_blueprint) > 50) else "⬜"
        with st.expander(f"{status_icon} 第{p.ep_num}話: {p.title or '(未タイトル)'}"):
            if p.detailed_blueprint:
                st.write(f"**設計図:**\n{p.detailed_blueprint}")
                if p.script_content:
                    st.write(f"**台本案:**\n{p.script_content[:300]}...")

    if st.button("🔄 プロットを一括更新/追加生成", type="primary", use_container_width=True):
        service = HegemonyService(engine)
        job = run_in_background(service.plot_expansion_workflow, book_id=book_id, gen_from=1, gen_to=len(plots))
        st.session_state.active_job = job
        st.rerun()

def render_writing_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    st.header("✍️ ステップ3: 本文執筆")
    plots = safe_run_async(engine.repo.get_all_plots(book_id))
    if not plots:
        st.info("プロットが生成されていません。")
        return

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
    
    if st.button("🖊️ 執筆開始", type="primary"):
        job = run_in_background(HegemonyService(engine).episode_writing_workflow, book_id=book_id, write_from=write_from, write_to=write_to, passion=passion, word_count=word_count, do_refine=do_refine, env_state=env, pipeline_mode=pipeline_mode)
        st.session_state.active_job = job
        st.rerun()

    st.divider()
    st.subheader("執筆済みエピソード")
    chapters = safe_run_async(engine.repo.get_all_non_anchor_chapters(book_id))
    if not chapters:
        st.info("まだ本文が執筆されていません。")
    else:
        for ch in chapters:
            # 監査結果による警告表示
            audit_note = ch.ai_insight or ""
            title_prefix = "⚠️" if "Audit" in audit_note else "📄"
            with st.expander(f"{title_prefix} 第{ch.ep_num}話: {ch.title} ({len(ch.content or '')}文字)"):
                st.caption(f"🤖 AI Insight: {audit_note}")
                if hasattr(ch, 'killer_phrase') and ch.killer_phrase:
                    st.markdown(f"**✨ 決め台詞:** `{ch.killer_phrase}`")
                st.text_area("本文", ch.content, height=300, key=f"view_ch_{ch.ep_num}")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    st.download_button("💾 ダウンロード", ch.content, file_name=f"ep{ch.ep_num}.txt", key=f"dl_{ch.ep_num}")
                with c_btn2:
                    if st.button("🗑️ 削除", key=f"del_{ch.ep_num}", type="secondary"):
                        safe_run_async(engine.repo.delete_chapter(book_id, ch.ep_num))
                        st.rerun()

def render_import_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    st.header("📥 本文インポート（手書き原稿の取り込み）")
    plots = safe_run_async(engine.repo.get_all_plots(book_id))
    ep_num = st.selectbox("対象話数", [p.ep_num for p in plots], format_func=lambda x: f"第{x}話")
    text = st.text_area("インポートする本文", height=400)
    do_refine = st.checkbox("商用クオリティ研磨を適用して保存", value=True)
    
    if st.button("📥 インポートして解析実行", type="primary"):
        if text:
            with st.spinner("AIが原稿を解析中..."):
                res = safe_run_async(HegemonyService(engine).chapter_import_workflow(book_id, ep_num, text, do_refine))
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.success(f"✅ 第{ep_num}話をインポートしました。")
                    st.metric("推定商用スコア", f"{res.get('potential_score', 0)}点")
                    st.info(f"💡 AIのアドバイス: {res.get('advice')}")
                    st.rerun()

def render_rebuild_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    st.header("🔨 プロット再構築（連載延長・テコ入れ）")
    st.info("過去の展開を引き継ぎつつ、ここから先の物語を再設計します。")
    
    plots = safe_run_async(engine.repo.get_all_plots(book_id))
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

    if st.button("🔨 プロット再構築を予約実行", type="primary", use_container_width=True):
        params = {
            "book_id": book_id, "start_ep": start_ep, "new_total": new_total,
            "new_keywords": new_keywords, "trend_memo": trend_memo,
            "plot_pattern": plot_pattern, "cheat_scale": cheat_scale,
            "cost_severity": cost_severity, "system_assist": system_assist
        }
        st.session_state.active_job = run_in_background(HegemonyService(engine).plot_rebuild_workflow, params=params)
        st.rerun()