import json
import time

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
from streamlit_app.progress import run_in_background
from streamlit_app.proxy import UltimateHegemonyEngineProxy as UltimateHegemonyEngine
from streamlit_app.workflow_types import WorkflowType


def _run_async(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()

    return loop.run_until_complete(coro)

def render_style_lab_tab(engine: UltimateHegemonyEngine) -> None:
    from streamlit_app.ui.icons import ICON_DNA
    st.header(f"{ICON_DNA} 文体ラボ")
    sample = st.text_area("分析用サンプル")
    if st.button("分析開始"):
        dna = engine.marketing.analyze_style_dna(sample)
        st.json(dna)

def render_strategy_tab(engine: UltimateHegemonyEngine, book_id: int) -> None:
    from streamlit_app.ui.icons import ICON_ANALYTICS
    st.header(f"{ICON_ANALYTICS} 覇権戦略司令部")
    plots = engine.get_all_plots(book_id)
    chapters = engine.get_all_non_anchor_chapters(book_id)
    bible = engine.get_latest_bible(book_id)
    book = engine.get_book(book_id)

    if book:
        from streamlit_app.ui.icons import ICON_CHART
        st.subheader(f"{ICON_CHART} 分析対象: {book.title}")
    else:
        st.error("作品データが見つかりません。")

    from streamlit_app.ui.icons import ICON_CURVE, ICON_ERROR, ICON_FILE, ICON_FIREWORKS
    t_pacing, t_logic, t_stress, t_export, t_critique, t_erotic = st.tabs([
        f"{ICON_CURVE} 感情曲線", f"{ICON_ERROR} 矛盾・整合性", f"{ICON_FIREWORKS} ストレスログ", f"{ICON_FILE} 商用ピッチ", "🤖 自己最適化", "🔞 官能度監査"
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

        from streamlit_app.ui.icons import ICON_INFO
        with st.expander(f"{ICON_INFO} ペーシング指針を確認"):
            if bible and bible.settings:
                try:
                    settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings)
                except Exception:
                    settings = {}
                st.write("**現在のアーク構成:**")
                for arc in settings.get("arcs", []):
                    st.caption(f"第{arc.get('start_ep')}~{arc.get('end_ep')}話: {arc.get('title')} - {arc.get('summary')}")

    with t_logic:
        from streamlit_app.ui.icons import ICON_DETECTIVE
        st.subheader(f"{ICON_DETECTIVE} 物語整合性レジャー（長期記憶管理）")
        if not chapters:
            st.info("執筆済みエピソードがないため、記憶データが生成されていません。")
        else:
            # 最新の状態を取得
            last_ch = chapters[-1]
            try:
                ws = last_ch.world_state if isinstance(last_ch.world_state, dict) else json.loads(last_ch.world_state or "{}")
            except:
                ws = {}

            from streamlit_app.ui.icons import ICON_BOOK, ICON_FLAG
            t_mem, t_thread = st.tabs([f"{ICON_BOOK} 長期記憶管理", f"{ICON_FLAG} 伏線元帳エディタ"])

            with t_mem:
                st.markdown("#### 累積あらすじ")
                summary = st.text_area("AIが維持している物語の要約", ws.get("cumulative_summary", ""), height=200)
                if st.button("記憶を上書き保存"):
                    ws["cumulative_summary"] = summary
                    engine.create_chapter(
                        book_id=book_id, ep_num=last_ch.ep_num, title=last_ch.title, content=last_ch.content, summary=last_ch.summary,
                        killer_phrase=last_ch.killer_phrase, ai_insight=str(last_ch.ai_insight or ""), world_state=ws, trinity_review_log=last_ch.trinity_review_log, created_at=last_ch.created_at
                    )
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

                # ── 伏線ビジュアルタイムライン ──
                if threads:
                    st.markdown(f"##### {ICON_FLAG} 伏線タイムラインマップ")
                    if HAS_PLOTLY:
                        fig_threads = go.Figure()

                        # ステータスごとの凡例登録用フラグ
                        added_legends = set()

                        for idx, t in enumerate(threads):
                            desc = t.get("description", "")
                            label = desc[:20] + "..." if len(desc) > 20 else desc
                            setup = t.get("setup_episode")
                            payoff = t.get("target_resolve_episode")
                            status = t.get("status", "Active")

                            color = "#e94560"  # Active (Red/Pink)
                            status_ja = "未回収 (Active)"
                            if status == "Closed":
                                color = "#4caf50"  # Closed (Green)
                                status_ja = "回収済 (Closed)"
                            elif status == "Resolving":
                                color = "#ffeb3b"  # Resolving (Yellow)
                                status_ja = "回収中 (Resolving)"
                            elif status == "Dormant":
                                color = "#9e9e9e"  # Dormant (Grey)
                                status_ja = "休眠 (Dormant)"

                            show_legend = status_ja not in added_legends
                            if show_legend:
                                added_legends.add(status_ja)

                            if payoff and payoff > setup:
                                fig_threads.add_trace(go.Scatter(
                                    x=[setup, payoff],
                                    y=[label, label],
                                    mode="lines+markers",
                                    line=dict(color=color, width=3),
                                    marker=dict(size=[8, 10], symbol=["circle", "star"], color=color),
                                    name=status_ja,
                                    legendgroup=status_ja,
                                    showlegend=show_legend,
                                    hovertemplate=f"内容: {desc}<br>発生: 第{setup}話<br>回収予定: 第{payoff}話<br>状態: {status_ja}<extra></extra>"
                                ))
                            else:
                                fig_threads.add_trace(go.Scatter(
                                    x=[setup],
                                    y=[label],
                                    mode="markers",
                                    marker=dict(size=10, symbol="circle", color=color),
                                    name=status_ja,
                                    legendgroup=status_ja,
                                    showlegend=show_legend,
                                    hovertemplate=f"内容: {desc}<br>発生: 第{setup}話 (回収予定未定)<br>状態: {status_ja}<extra></extra>"
                                ))

                        fig_threads.update_layout(
                            xaxis=dict(
                                title="話数 (Episode)",
                                dtick=1,
                                gridcolor="rgba(255,255,255,0.1)",
                                zeroline=False
                            ),
                            yaxis=dict(
                                title="",
                                automargin=True,
                                gridcolor="rgba(255,255,255,0.05)"
                            ),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font_color='#a8b2c1',
                            height=max(200, 100 + len(threads) * 35),
                            margin=dict(l=20, r=20, t=10, b=20),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            )
                        )
                        st.plotly_chart(fig_threads, use_container_width=True)
                    else:
                        st.info("📊 タイムラインをより見やすく描画するには `pip install plotly` を環境に導入してください。")
                        # 簡易表示
                        df_summary = pd.DataFrame([
                            {
                                "内容": t.get("description"),
                                "発生話数": f"第{t.get('setup_episode')}話",
                                "回収予定話数": f"第{t.get('target_resolve_episode')}話" if t.get('target_resolve_episode') else "未定",
                                "ステータス": t.get("status")
                            } for t in threads
                        ])
                        st.dataframe(df_summary, use_container_width=True)
                else:
                    st.caption("現在、登録されている伏線はありません。")

                # 新しい伏線の手動追加フォーム
                st.markdown("#### 伏線と因果の管理")
                with st.expander("➕ 新しい伏線を手動で追加する"):
                    with st.form("add_thread_form"):
                        t_desc = st.text_input("伏線の内容（例：主人公の左腕の痣の秘密）")
                        t_ep = st.number_input("発生話数 (Setup)", 1, 200, last_ch.ep_num)
                        t_payoff = st.number_input("回収予定話数 (Payoff / 任意 - 0は未設定)", 0, 200, 0)
                        t_urgency = st.slider("重要度/緊急度", 1, 5, 3)
                        if st.form_submit_button("伏線帳に追加"):
                            new_t = {
                                "id": f"manual_{int(time.time())}",
                                "description": t_desc,
                                "status": "Active",
                                "urgency": t_urgency,
                                "setup_episode": t_ep,
                                "target_resolve_episode": t_payoff if t_payoff > 0 else None
                            }
                            threads.append(new_t)
                            ws["story_threads"] = threads
                            engine.create_chapter(
                                book_id=book_id, ep_num=last_ch.ep_num, title=last_ch.title, content=last_ch.content, summary=last_ch.summary,
                                killer_phrase=last_ch.killer_phrase, ai_insight=str(last_ch.ai_insight or ""), world_state=ws, trinity_review_log=last_ch.trinity_review_log, created_at=last_ch.created_at
                            )
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
                                engine.create_chapter(
                                    book_id=book_id, ep_num=last_ch.ep_num, title=last_ch.title, content=last_ch.content, summary=last_ch.summary,
                                    killer_phrase=last_ch.killer_phrase, ai_insight=str(last_ch.ai_insight or ""), world_state=ws, trinity_review_log=last_ch.trinity_review_log, created_at=last_ch.created_at
                                )
                                st.rerun()

            # 最新の監査ログを表示
            st.divider()
            from streamlit_app.ui.icons import ICON_ERROR
            st.markdown(f"#### {ICON_ERROR} AI監査役の最新レポート")
            audit_log = (last_ch.trinity_review_log or {}).get("audit_log", {}) if isinstance(last_ch.trinity_review_log, dict) else {}
            if audit_log.get("conflict_points"):
                st.error("**重大な論理矛盾を検知しました**")
                for err in audit_log["conflict_points"]:
                    st.write(f"- {err}")
                if audit_log.get("rewrite_suggestion"):
                    from streamlit_app.ui.icons import ICON_LIGHTBULB
                    st.info(f"{ICON_LIGHTBULB} **修正案:** {audit_log['rewrite_suggestion']}")
            else:
                from streamlit_app.ui.icons import ICON_STAR
                st.success(f"{ICON_STAR} 物語の整合性は正常です。AIは過去の全事実を正確に把握しています。")

            if audit_log.get("missing_items"):
                from streamlit_app.ui.icons import ICON_WARNING
                st.warning(f"{ICON_WARNING} **未回収の予定伏線:** {', '.join(audit_log['missing_items'])}")

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
        st.subheader(f"{ICON_FILE} 出版社・コンテスト用ピッチ出力")
        if not bible:
            st.warning("作品のBibleデータが見つかりません。")
            return

        from streamlit_app.ui.icons import ICON_PENCIL
        if st.button(f"{ICON_PENCIL} 商業用ピッチデッキを生成"):
            try:
                settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings)
            except Exception:
                settings = {}
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
    from streamlit_app.ui.icons import ICON_ROCKET
    if st.button(f"{ICON_ROCKET} 10 Iterations 自己最適化分析を実行", type="primary", use_container_width=True):
        job = run_in_background(WorkflowType.CRITIQUE_OPTIMIZE, book_id=book_id)
        UIStateStore.set_active_job(job)
        st.rerun()

    display_meta = None
    history = engine.repo.get_optimization_history(book_id)
    if history:
        display_meta = history[0].get('report_json', {})

    if display_meta:
        meta = display_meta
        _display_radar_chart(meta)

        col_l, col_r = st.columns(2)
        with col_l:
            with st.container(border=True):
                from streamlit_app.ui.icons import ICON_DETECTIVE
                st.markdown(f"#### {ICON_DETECTIVE} 抽出されたAIの「サボり癖」")
                st.write(meta.get("habits") or meta.get("共通の「サボり癖」") or "分析待ち")
            with st.container(border=True):
                from streamlit_app.ui.icons import ICON_DNA
                st.markdown(f"#### {ICON_DNA} 文体DNAの乖離レポート")
                st.write(meta.get("style_gap") or meta.get("文体DNAの乖離") or "良好")

        with col_r:
            with st.container(border=True):
                from streamlit_app.ui.icons import ICON_SETTINGS
                st.markdown(f"#### {ICON_SETTINGS} Config修正案")
                patch_data = meta.get("config_patch") or meta.get("config.py への具体的修正案") or ""
                st.code(patch_data, language="python")
                from streamlit_app.ui.icons import ICON_SETTINGS
                if st.button(f"{ICON_SETTINGS} この数値を承認待ちパッチとして登録"):
                    from streamlit_app import api_client
                    result = api_client.save_pending_patch(
                        book_id=book_id,
                        patch_type="config",
                        patch_content=str(patch_data),
                        ab_test_result={"scores": meta.get("scores") or {}, "habits": meta.get("habits"), "style_gap": meta.get("style_gap")}
                    )
                    if result.get("success"):
                        st.success("✅ Configパッチを承認待ちとして登録しました。")
                    else:
                        st.error(f"❌ 保存エラー: {result.get('error')}")

            with st.container(border=True):
                from streamlit_app.ui.icons import ICON_WRITING
                st.markdown(f"#### {ICON_WRITING} プロンプト強化案")
                prompt_patch = meta.get("prompt_patch") or meta.get("engine_prompts.py への具体的修正案") or ""
                st.success(prompt_patch)
                from streamlit_app.ui.icons import ICON_SAVE
                if st.button(f"{ICON_SAVE} プロンプトパッチを承認待ちとして保存"):
                    from streamlit_app import api_client
                    result = api_client.save_pending_patch(
                        book_id=book_id,
                        patch_type="prompt",
                        patch_content=str(prompt_patch),
                        ab_test_result={"scores": meta.get("scores") or {}, "habits": meta.get("habits"), "style_gap": meta.get("style_gap")}
                    )
                    if result.get("success"):
                        st.success("✅ プロンプトパッチを承認待ちとして登録しました。")
                    else:
                        st.error(f"❌ 保存エラー: {result.get('error')}")

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
        from streamlit_app.ui.icons import ICON_RECYCLE
        if st.button(f"{ICON_RECYCLE} 強化プロンプトで再執筆テスト"):
            with st.spinner("テスト執筆中..."):
                res = engine.critique.run_dry_run(book_id, test_ep, str(prompt_patch))
                st.text_area("テスト結果", res, height=300)

        # ---------- Streamlit Human-in-the-Loop Diff & Version Control ----------
        st.divider()
        from streamlit_app.ui.icons import ICON_SHIELD
        st.subheader(f"{ICON_SHIELD} 戦略司令部 (Human-in-the-Loop & A/Bテスト)")

        col1, col2 = st.columns(2)

        with col1:
            from streamlit_app.ui.icons import ICON_BOOK
            st.markdown(f"### {ICON_BOOK} 承認待ちパッチ一覧")

            try:
                from streamlit_app import api_client
                pending_patches = api_client.get_pending_patches(book_id)
            except Exception:
                pending_patches = []

            if not pending_patches:
                st.info("承認待ちのパッチはありません。")
            else:
                for patch in pending_patches:
                    with st.container(border=True):
                        st.markdown(f"**タイプ:** `{patch['patch_type'].upper()}` | **作成日:** `{patch['created_at']}`")

                        # Diff-like display
                        st.markdown("**提案内容 (パッチ):**")
                        st.code(patch['patch_content'], language="python" if patch['patch_type'] == 'config' else "markdown")

                        # Actions
                        col_btn1, col_btn2 = st.columns(2)

                        # Approve Action
                        if col_btn1.button(f"👍 承認して適用 (ID: {patch['id']})", key=f"approve_{patch['id']}"):
                            from streamlit_app import api_client
                            result = api_client.approve_patch(patch['id'])
                            if result.get("success"):
                                st.toast("✅ パッチを承認して適用しました！")
                                st.rerun()
                            else:
                                st.error(f"適用エラー: {result.get('error')}")

                        # Reject Action
                        if col_btn2.button(f"👎 却下 (ID: {patch['id']})", key=f"reject_{patch['id']}"):
                            from streamlit_app import api_client
                            result = api_client.reject_patch(patch['id'])
                            if result.get("success"):
                                st.toast("❌ パッチを却下しました。")
                                st.rerun()
                            else:
                                st.error(f"却下エラー: {result.get('error')}")

        with col2:
            st.markdown("### 🕒 プロンプト更新履歴")

            try:
                from streamlit_app import api_client
                prompt_versions = api_client.get_prompt_versions(book_id)
            except Exception:
                prompt_versions = []

            if not prompt_versions:
                st.info("プロンプトのバージョン履歴はありません。")
            else:
                for ver in prompt_versions:
                    with st.container(border=True):
                        title_str = f"**バージョン:** `{ver['version_tag']}`"
                        if ver['is_active']:
                            title_str += " 🟢 **[適用中]**"
                        elif ver['rollback_reason']:
                            title_str += " 🔴 **[無効/ロールバック済]**"

                        st.markdown(title_str)
                        st.markdown(f"**作成日時:** `{ver['created_at']}`")

                        # Scores
                        score_before = ver.get('score_before')
                        score_after = ver.get('score_after')
                        st.markdown(f"**評価スコア:** 事前: `{score_before or 'N/A'}` | 事後: `{score_after or 'N/A'}`")

                        if ver['rollback_reason']:
                            st.warning(f"理由: {ver['rollback_reason']}")

                        st.text_area("プロンプト内容", ver['content'], height=80, key=f"ver_content_{ver['id']}", disabled=True)

                        if not ver['is_active'] and not ver['rollback_reason']:
                            if st.button(f"⏪ このバージョンにロールバック (ID: {ver['id']})", key=f"rollback_{ver['id']}"):
                                from streamlit_app import api_client
                                result = api_client.rollback_prompt_version(book_id, ver['id'])
                                if result.get("success"):
                                    st.toast("⏪ ロールバックが完了しました！")
                                    st.rerun()
                                else:
                                    st.error(f"ロールバックエラー: {result.get('error')}")


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


def render_prompt_metrics_dashboard():
    """プロンプト使用メトリクスダッシュボード"""
    st.header("📊 プロンプト使用メトリクス")

    try:
        import requests
        response = requests.get("http://localhost:8000/api/prompt-metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            metrics = data.get("data", [])

            if not metrics:
                st.info("メトリクスデータがありません。")
                return

            # Convert to DataFrame for display
            import pandas as pd
            df = pd.DataFrame(metrics)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総ヒット数", sum(m.get('hits', 0) for m in metrics))
            with col2:
                st.metric("平均レスポンス時間 (ms)", f"{df['avg_time_ms'].mean():.1f}")
            with col3:
                st.metric("エラー率", f"{(sum(m.get('error_count', 0) for m in metrics) / max(sum(m.get('hits', 0) for m in metrics), 1) * 100):.1f}%")
            with col4:
                st.metric("テンプレート数", len(metrics))

            # Template usage chart
            if HAS_PLOTLY and len(metrics) > 0:
                st.subheader("テンプレート別使用回数")
                fig = go.Figure([go.Bar(x=df['template_name'], y=df['hits'])])
                fig.update_layout(xaxis_title="テンプレート名", yaxis_title="ヒット数", height=400)
                st.plotly_chart(fig)

            # Detailed table
            st.subheader("詳細データ")
            display_df = df[['template_name', 'hits', 'avg_time_ms', 'error_count', 'last_accessed']].copy()
            if 'last_accessed' in display_df.columns:
                display_df['last_accessed'] = pd.to_datetime(display_df['last_accessed']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(display_df, use_container_width=True)

            # Delete old data option
            with st.expander("データ管理"):
                days = st.slider("保持期間（日数）", 1, 90, 30)
                if st.button("古いデータを削除"):
                    delete_response = requests.delete(f"http://localhost:8000/api/prompt-metrics?days={days}")
                    if delete_response.status_code == 200:
                        st.toast("古いデータを削除しました")
                        st.rerun()
        else:
            st.error(f"APIエラー: {response.status_code}")
    except Exception as e:
        st.error(f"メトリクスの取得に失敗しました: {e}")

    with t_erotic:
        from streamlit_app.state import get_session
        session = get_session()
        if not session.config.get("enable_nsfw", False):
            st.warning("🔞 官能度監査を利用するには、サイドバーで「NSFWモード」を有効にしてください。")
        else:
            st.subheader("🔍 官能度監査 (Erotic Audit)")
            from config.erotic_vocabulary import METAPHOR_BANK
            from src.services.erotic_diversity_score import (
                check_repetition,
                compute_diversity_score,
            )

            if chapters:
                latest = chapters[-1]
                text = getattr(latest, 'content', '') or ''
                diversity = compute_diversity_score(text, METAPHOR_BANK)
                repetitions = check_repetition(text, METAPHOR_BANK)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("比喩表現 多様性スコア", f"{diversity:.2f}", help="0.0 - 1.0 (高いほど多様な比喩を使用)")
                with col2:
                    st.metric("反復警告数", len(repetitions))

                if repetitions:
                    with st.expander("⚠️ 反復表現警告の詳細"):
                        for w in repetitions:
                            st.warning(w)
                else:
                    st.success("表現の重複や同じ語彙の過剰な連続使用は検出されませんでした。")
            else:
                st.info("まだ執筆された本文がありません。エピソードを執筆後に監査が実行されます。")
