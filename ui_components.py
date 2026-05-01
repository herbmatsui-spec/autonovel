"""
ui_components.py - Streamlit UIコンポーネントモジュール
各タブ・ウィジェットを関数に分離し、app.py から呼び出す形で管理。
UIロジックとビジネスロジックを明確に分離する。

【実装済み改善案】
  案1: ワンクリック全自動モード (render_easy_mode)
  案2: 4ステップウィザードUI  (render_planning_wizard)
  案6: ストレス感情曲線の可視化 (render_stress_curve in render_strategy_tab)
"""
from __future__ import annotations
import time
import json
from typing import Any, Dict, List, Optional

import streamlit as st

from config import (
    STYLE_DEFINITIONS, STORY_ARCHETYPES, CHEAT_DESCRIPTIONS,
    COST_DESCRIPTIONS, PLOT_STRUCTURES, GlobalConfig,
    COST_INPUT_FLASH, COST_OUTPUT_FLASH, EASY_MODE_KEYWORDS_MAP,
    EASY_GENRES, WIZARD_GENRE_OPTIONS, WIZARD_ARCHETYPE_LABELS
)
from models import BookDbModel, PlotDbModel, ChapterDbModel
from background import ProgressState, run_in_background, estimate_tokens, TokenUsageTracker
from engine import UltimateHegemonyEngine, safe_run_async
from engine_service import HegemonyService

# 分割したUIモジュールのインポート
from ui_tabs_planning import render_easy_mode, render_planning_tab, render_planning_wizard
from ui_tabs_writing import render_plot_tab, render_writing_tab, render_import_tab, render_rebuild_tab
from ui_tabs_analytics import render_style_lab_tab, render_strategy_tab
from ui_tabs_marketing import render_promo_tab

# ==========================================
# ユーティリティ
# ==========================================
def inject_focus_css() -> None:
    """集中執筆モード: 明朝体・落ち着いた配色に変更"""
    st.markdown("""
    <style>
    body { font-family: "Yu Mincho", "游明朝", serif !important; background: #fdfaf5; }
    .stTextArea textarea { font-family: "Yu Mincho", "游明朝", serif !important; line-height: 2.0; }
    </style>
    """, unsafe_allow_html=True)


def display_token_cost(text: str, label: str = "内容") -> None:
    tokens = estimate_tokens(text)
    avg_rate = (COST_INPUT_FLASH + COST_OUTPUT_FLASH) / 2
    cost   = tokens * avg_rate
    st.caption(f"{label} 推定トークン: {tokens} (概算コスト: ${cost:.6f})")


# ==========================================
# 進捗表示フラグメント（リアルタイム更新）
# ==========================================
@st.fragment
def progress_fragment(run_key: str, engine: Optional[UltimateHegemonyEngine] = None) -> None:
    """リアルタイムに進捗を表示するための独立UIコンポーネント"""
    if "active_job" not in st.session_state:
        return

    job: ProgressState = st.session_state.active_job

    if not job.is_running:
        if job.error:
            st.error(f"🚨 エラーにより停止: {job.error}")
            with st.expander("📜 エラーログを表示"):
                st.code("\n".join(job.logs))
            if st.button("🔄 閉じる", key=f"close_err_{run_key}"):
                del st.session_state["active_job"]
                st.rerun()
        elif job.result_data is not None:
            st.success("✨ 完了！　すべてのタスクが正常に終了しました。")
            if isinstance(job.result_data, dict):
                res = job.result_data
                if "book_id" in res:
                    st.success(f"📖 新しい作品『{res.get('title', '無題')}』が生成されました。")
                    st.session_state["current_book_id"] = res["book_id"]
                    st.session_state["app_mode"] = "advanced" # 上級者モードへ誘導
                if "chars_count" in res:
                    # 提案7: 完了後の「次のステップ」明確化ガイド
                    st.subheader("🎉 次のステップへ進みましょう！")
                    col_next1, col_next2, col_next3 = st.columns(3)
                    with col_next1:
                        if st.button("📖 作品を読みに行く", use_container_width=True):
                            st.session_state["app_mode"] = "advanced"
                            st.session_state["current_book_id"] = res["book_id"]
                            st.rerun()
                    with col_next2:
                        if st.button("🔄 別の作品を生成する", use_container_width=True):
                            st.session_state["app_mode"] = "easy"
                            st.rerun()
                    st.info(f"✍️ 合計 {res['chars_count']:,} 文字を執筆しました。")

                if "failed_episodes" in res and res["failed_episodes"]:
                    st.error("🚨 以下のエピソードは生成に失敗しました:")
                    for fail_ep in res["failed_episodes"]:
                        st.write(f"- 第{fail_ep.get('ep_num', '不明')}話: {fail_ep.get('error_message', '詳細不明')}")
                    
                    if engine and st.button("🔄 失敗したエピソードを再試行", key=f"retry_btn_{run_key}", use_container_width=True):
                        passion = st.session_state.get("last_passion", 0.6)
                        word_count = st.session_state.get("last_word_count", 2500)
                        
                        job = run_in_background(
                            HegemonyService(engine).retry_failed_episodes_workflow,
                            book_id=res["book_id"],
                            passion=passion,
                            word_count=word_count
                        )
                        st.session_state.active_job = job
                        st.rerun()
                
                # サービスから戻ったデータをUI状態に同期
                if "zip_data" in res:
                    st.session_state["auto_zip_data"] = res["zip_data"]
                    st.session_state["auto_zip_name"] = res.get("zip_filename", "export.zip")

            with st.expander("📜 実行詳細ログを表示"):
                st.code("\n".join(job.logs))
            if st.button("🔄 結果を確認する", key=f"confirm_{run_key}"):
                del st.session_state["active_job"]
                st.rerun()
        
        # トークン使用量の同期（バックグラウンドからフロントへ）
        if job.token_usage["calls"] > 0:
            for key in ["prompt", "completion", "calls"]:
                st.session_state.token_stats[key] += job.token_usage.get(key, 0)
            # 二重加算防止のためリセット
            job.token_usage = {"prompt": 0, "completion": 0, "calls": 0}

        return

    # 実行中ダッシュボード
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### ⚙️ {job.message}")
            if job.sub_message:
                st.markdown(f"**現在実行中:** `{job.sub_message}`")
        with col2:
            elapsed = time.time() - job.start_time
            st.metric("経過時間", f"{elapsed:.1f}s")

        if job.total_steps > 0:
            pct = min(1.0, job.current_step / job.total_steps)
            st.progress(pct, text=f"全体進捗: {job.current_step}/{job.total_steps} ({int(pct*100)}%)")
            if job.current_step > 0:
                eta = (elapsed / job.current_step) * (job.total_steps - job.current_step)
                st.caption(f"🏁 予測残り時間: 約 {eta:.0f} 秒")
        else:
            st.spinner(job.sub_message or "処理中...")

        with st.expander("🔍 リアルタイム・ログ", expanded=True):
            for log in job.logs[-5:]:
                st.caption(log)

        if st.button("🛑 処理を中断する", key=f"stop_{run_key}", type="secondary"):
            job.stop()

    time.sleep(1.0)
    st.rerun()
