import streamlit as st
import pandas as pd
import re
import json
import time
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
from engine import UltimateHegemonyEngine, safe_run_async
from engine_service import HegemonyService
from background import run_in_background
from config import GlobalConfig

def render_style_lab_tab(engine: UltimateHegemonyEngine) -> None:
    st.header("🧬 文体ラボ")
    sample = st.text_area("分析用サンプル")
    if st.button("分析開始"):
        dna = safe_run_async(engine.marketing.analyze_style_dna(sample))
        st.json(dna)

def render_strategy_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    st.header("📈 覇権戦略司令部")
    plots = safe_run_async(engine.repo.get_all_plots(book_id))
    chapters = safe_run_async(engine.repo.get_all_non_anchor_chapters(book_id, order_by="ep_num"))
    bible = safe_run_async(engine.repo.get_latest_bible(book_id))
    book = safe_run_async(engine.repo.get_book(book_id))

    if book:
        st.subheader(f"📊 分析対象: {book.title}")
    else:
        st.error("作品データが見つかりません。")

    t_pacing, t_logic, t_stress, t_export, t_critique = st.tabs([
        "📉 感情曲線", "🚨 矛盾・整合性", "🎆 ストレスログ", "📄 商用ピッチ", "🤖 自己最適化"
    ])
    
    with t_pacing:
        if plots:
            df = pd.DataFrame([
                {
                    "話数": p.ep_num,
                    "緊張感": p.tension or 50,
                    "ストレス": p.stress or 0,
                    "カタルシス回": "★" if p.is_catharsis else ""
                } for p in plots
            ])
            st.line_chart(df, x="話数", y=["緊張感", "ストレス"])
            catharsis_eps = [p.ep_num for p in plots if p.is_catharsis]
            if catharsis_eps:
                st.info(f"🎆 **カタルシス予約回:** 第 {', '.join(map(str, catharsis_eps))} 話")
        else:
            st.info("プロットが生成されていません。「プロット管理」タブで生成してください。")

        with st.expander("ℹ️ ペーシング指針を確認"):
            if bible and bible.settings:
                settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings)
                st.write("**現在のアーク構成:**")
                for arc in settings.get("arcs", []):
                    st.caption(f"第{arc.get('start_ep')}~{arc.get('end_ep')}話: {arc.get('title')} - {arc.get('summary')}")

    with t_logic:
        st.subheader("🕵️ 物語整合性レジャー（長期記憶管理）")
        if not chapters:
            st.info("執筆済みエピソードがないため、記憶データが生成されていません。")
        else:
            # 最新の状態を取得
            last_ch = chapters[-1]
            try:
                ws = last_ch.world_state if isinstance(last_ch.world_state, dict) else json.loads(last_ch.world_state or "{}")
            except:
                ws = {}
            
            t_mem, t_thread = st.tabs(["📖 長期記憶管理", "🚩 伏線元帳エディタ"])
            
            with t_mem:
                st.markdown("#### 累積あらすじ")
                summary = st.text_area("AIが維持している物語の要約", ws.get("cumulative_summary", ""), height=200)
                if st.button("記憶を上書き保存"):
                    ws["cumulative_summary"] = summary
                    safe_run_async(engine.repo.create_chapter(
                        book_id, last_ch.ep_num, last_ch.title, last_ch.content, last_ch.summary,
                        last_ch.killer_phrase, str(last_ch.ai_insight or ""), ws, last_ch.trinity_review_log, last_ch.created_at
                    ))
                    st.success("累積あらすじを更新しました。次話からこの内容が反映されます。")

                st.markdown("#### 🔍 判明済み事実の履歴")
                new_facts = ws.get("new_facts", [])
                if new_facts:
                    st.write(", ".join(new_facts))
                else:
                    st.caption("判明事実はまだありません。")
            
            with t_thread:
                st.markdown("#### 伏線と因果の管理")
                threads = ws.get("story_threads", [])
                
                # 新しい伏線の手動追加フォーム
                with st.expander("➕ 新しい伏線を手動で追加する"):
                    with st.form("add_thread_form"):
                        t_desc = st.text_input("伏線の内容（例：主人公の左腕の痣の秘密）")
                        t_ep = st.number_input("発生話数", 1, 200, last_ch.ep_num)
                        t_urgency = st.slider("重要度/緊急度", 1, 5, 3)
                        if st.form_submit_button("伏線帳に追加"):
                            new_t = {
                                "id": f"manual_{int(time.time())}",
                                "description": t_desc,
                                "status": "Active",
                                "urgency": t_urgency,
                                "setup_episode": t_ep
                            }
                            threads.append(new_t)
                            ws["story_threads"] = threads
                            safe_run_async(engine.repo.create_chapter(
                                book_id, last_ch.ep_num, last_ch.title, last_ch.content, last_ch.summary,
                                last_ch.killer_phrase, str(last_ch.ai_insight or ""), ws, last_ch.trinity_review_log, last_ch.created_at
                            ))
                            st.rerun()

                # 既存の伏線リスト
                for i, t in enumerate(threads):
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.markdown(f"**{t.get('description')}**")
                        c2.caption(f"発生: 第{t.get('setup_episode')}話 Urgency:{t.get('urgency')}")
                        current_stat = t.get('status', 'Active')
                        new_status = c3.selectbox("状態", ["Active", "Closed", "Resolving", "Dormant"], 
                                                index=["Active", "Closed", "Resolving", "Dormant"].index(current_stat), 
                                                key=f"t_stat_{i}")
                        if new_status != current_stat:
                            t['status'] = new_status
                            if st.button("反映", key=f"save_t_{i}"):
                                ws["story_threads"] = threads
                                safe_run_async(engine.repo.create_chapter(
                                    book_id, last_ch.ep_num, last_ch.title, last_ch.content, last_ch.summary,
                                    last_ch.killer_phrase, str(last_ch.ai_insight or ""), ws, last_ch.trinity_review_log, last_ch.created_at
                                ))
                                st.rerun()

            # 最新の監査ログを表示
            st.divider()
            st.markdown("#### 🚨 AI監査役の最新レポート")
            audit_log = (last_ch.trinity_review_log or {}).get("audit_log", {}) if isinstance(last_ch.trinity_review_log, dict) else {}
            if audit_log.get("conflict_points"):
                st.error("**重大な論理矛盾を検知しました**")
                for err in audit_log["conflict_points"]:
                    st.write(f"- {err}")
                if audit_log.get("rewrite_suggestion"):
                    st.info(f"💡 **修正案:** {audit_log['rewrite_suggestion']}")
            else:
                st.success("✨ 物itiesの整合性は正常です。AIは過去の全事実を正確に把握しています。")
            
            if audit_log.get("missing_items"):
                st.warning(f"⚠️ **未回収の予定伏線:** {', '.join(audit_log['missing_items'])}")

    with t_stress:
        current_stress = book.cumulative_stress or 0 if book else 0
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            st.metric("現在の累積ストレス値", f"{current_stress} / 65", 
                      delta=current_stress - 40 if current_stress > 40 else 0,
                      delta_color="inverse")
            st.progress(min(1.0, current_stress / 65), text=f"ヘイト飽和率: {int(min(1.0, current_stress/65)*100)}%")
        
        with col_s2:
            with st.container(border=True):
                st.markdown("**📉 感情曲線最適化ルール**")
                st.markdown("""
                - **65以上**: 次話を強制カタルシス回へ変換。
                - **20以下**: ストレス蓄積モード（ヘイト増量）へ切替。
                """)
        
        if current_stress >= 65:
            st.warning("🔥 **ストレスが限界値を超えています**。次話は自動的に『大ざまぁ（強制カタルシス）』として執筆され、読者の欲求を爆発させます。")
        else:
            st.info("🟢 ストレスは健全な範囲内です。敵の理不尽さを維持しつつ、Payoff（解決）に向けて溜めを作ってください。")

        st.divider()
        st.markdown("#### 📊 ストレス推移詳細データ")
        stress_data = engine.narrative.get_stress_history_data(chapters, plots)
        if stress_data:
            df_s = pd.DataFrame(stress_data)
            st.line_chart(df_s, x="話数", y="ストレス蓄積値")
            with st.expander("生データを確認"):
                st.table(stress_data)

    with t_export:
        st.subheader("出版社・コンテスト用ピッチ出力")
        if not bible:
            st.warning("作品のBibleデータが見つかりません。")
            return
            
        if st.button("📝 商業用ピッチデッキを生成"):
            settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings)
            pitch = (
                f"# 【商業化企画案】{book.title}\n\n"
                f"## 1. 作品コンセプト\n{book.concept}\n\n"
                f"## 2. 読者ターゲットと約束\n{settings.get('target_persona', 'N/A')}\n約束: {settings.get('reader_promise', 'N/A')}\n\n"
                f"## 3. あらすじ\n{book.synopsis}\n\n"
                f"## 4. 商業的特異点 (USP)\n{settings.get('story_direction', 'AI解析による最適化された感情曲線と論理整合性')}\n\n"
                f"## 5. 世界観・ルール\n{settings.get('magic_cost_and_taboo', '独自の設定体系')}"
            )
            st.code(pitch, language="markdown")
            st.download_button("📥 ダウンロード", pitch, file_name="pitch.txt")

    with t_critique:
        _render_optimization_cockpit(engine, book_id, book)

def _render_optimization_cockpit(engine, book_id, book):
    if st.button("🚀 10 Iterations 自己最適化分析を実行", type="primary", use_container_width=True):
        service = HegemonyService(engine)
        job = run_in_background(service.run_critique_optimization_workflow, book_id=book_id)
        st.session_state.active_job = job
        st.rerun()
    
    display_meta = None
    history = safe_run_async(engine.repo.get_optimization_history(book_id))
    if history:
        display_meta = history[0].get('report_json', {})

    if display_meta:
        meta = display_meta
        _display_radar_chart(meta)

        col_l, col_r = st.columns(2)
        with col_l:
            with st.container(border=True):
                st.markdown("#### 🕵️ 抽出されたAIの「サボり癖」")
                st.write(meta.get("habits") or meta.get("共通の「サボり癖」") or "分析待ち")
            with st.container(border=True):
                st.markdown("#### 🧬 文体DNAの乖離レポート")
                st.write(meta.get("style_gap") or meta.get("文体DNAの乖離") or "良好")
        
        with col_r:
            with st.container(border=True):
                st.markdown("#### ⚙️ Config修正案")
                patch_data = meta.get("config_patch") or meta.get("config.py への具体的修正案") or ""
                st.code(patch_data, language="python")
                if st.button("🛠️ この数値を GlobalConfig に即時適用"):
                    # JSON形式とPython代入形式の両方に対応する正規表現
                    matches = re.findall(r'["\']?(\w+)["\']?\s*[:=]\s*([\d\.]+)', str(patch_data))
                    if matches:
                        cfg = GlobalConfig()
                        for k, v in matches:
                            try:
                                val = float(v) if '.' in v else int(v)
                                cfg.set(k, val)
                                st.toast(f"✅ {k} を {val} に更新")
                            except: pass
                        st.rerun()
            
            with st.container(border=True):
                st.markdown("#### ✍️ プロンプト強化案")
                prompt_patch = meta.get("prompt_patch") or meta.get("engine_prompts.py への具体的修正案") or ""
                st.success(prompt_patch)
                if st.button("💾 プロンプトパッチを保存"):
                    GlobalConfig().set("optimized_prompt_patch", prompt_patch)
                    st.toast("保存完了：次回執筆から反映されます")

            with st.container(border=True):
                st.markdown("#### 🤖 コーディングAIへの改造指示")
                st.caption("この分析結果を元に、エンジンのソースコード自体をリファクタリングするための命令文です。")
                refactor_cmd = meta.get("refactor_instruction") or "分析データが不足しています。"
                st.code(refactor_cmd, language="markdown")
                st.info("💡 上記をコピーして、Gemini Code Assist等に貼り付けることでツール自体を進化させられます。")

        # ドライラン砂場
        st.divider()
        st.subheader("🧪 改善プロンプトの即時検証")
        test_ep = st.number_input("検証する話数", 1, 100, 1)
        if st.button("🔄 強化プロンプトで再執筆テスト"):
            with st.spinner("テスト執筆中..."):
                res = safe_run_async(engine.critique.run_dry_run(book_id, test_ep, str(prompt_patch)))
                st.text_area("テスト結果", res, height=300)

def _display_radar_chart(meta):
    if not HAS_PLOTLY:
        st.info("📊 レーダーチャートを表示するには `pip install plotly` を実行してください。")
        return

    raw_scores = meta.get("scores", {})
    if not isinstance(raw_scores, dict): raw_scores = {}
    categories = ['プロット再現度', '文体DNA一致率', '描写密度']
    values = [
        raw_scores.get('plot_adherence', 50), 
        raw_scores.get('style_consistency', 50), 
        raw_scores.get('detail_density', 50)
    ]
    fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#e94560'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor='rgba(0,0,0,0)', font_color='white', height=300)
    st.plotly_chart(fig)