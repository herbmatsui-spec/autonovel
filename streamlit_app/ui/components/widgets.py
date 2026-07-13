"""
streamlit_app/ui/components/widgets.py - 共通UIコンポーネント
ビジネスロジックを排除し、純粋な表示とイベント発行のみを行う。
"""
from __future__ import annotations

import time
from typing import Any

import streamlit as st

from streamlit_app.event_bus import UIEventType
from streamlit_app.progress import ProgressStateProxy
from streamlit_app.state import UIStateStore
from streamlit_app.ui.icons import ICON_PACKAGE, ICON_SETTINGS


def render_primary_button(label: str, key: str, on_click: Any = None, use_container_width: bool = True, icon: str = "") -> bool:
    """
    デザインシステムに基づいた共通プライマリボタン。
    アイコンの自動付与とスタイルの統一を行う。
    """
    full_label = f"{icon} {label}" if icon else label
    return st.button(full_label, key=key, on_click=on_click, type="primary", use_container_width=use_container_width)

def render_secondary_button(label: str, key: str, on_click: Any = None, use_container_width: bool = True, icon: str = "") -> bool:
    """
    デザインシステムに基づいた共通セカンダリボタン。
    """
    full_label = f"{icon} {label}" if icon else label
    return st.button(full_label, key=key, on_click=on_click, use_container_width=use_container_width)

def inject_focus_css() -> None:
    """集中執筆モード: 明朝体・落ち着いた配色に変更"""
    st.markdown("""
    <style>
    body { font-family: "Yu Mincho", "游明朝", serif !important; background: #fdfaf5; }
    .stTextArea textarea { font-family: "Yu Mincho", "游明朝", serif !important; line-height: 2.0; }
    header[data-testid="stHeader"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

def render_section_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """
    デザインシステムに基づいた共通セクションヘッダー。
    視覚的な一貫性と階層構造を提供し、ユーザーの認知負荷を軽減する。
    """
    full_title = f"{icon} {title}" if icon else title
    st.markdown(f"### {full_title}")
    if subtitle:
        st.markdown(f"<div style='color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem;'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("---")

@st.fragment
def progress_fragment(run_key: str, controller_manager: Any) -> None:
    """
    リアルタイムに進捗を表示するための独立UIコンポーネント。
    ロジックは ControllerManager 経由で処理する。
    """
    # st.session_state 直接アクセス排除: monitored_jobs で代用
    if run_key not in UIStateStore.get_runtime().monitored_jobs:
        saved_task_id = UIStateStore.get_runtime().active_job_ids.get(run_key)
        if saved_task_id:
            job = ProgressStateProxy(saved_task_id)
            job.refresh()
            if job.message != "初期化中..." and not job.error:
                UIStateStore.set_active_job(job)
                st.toast("🔄 以前のタスク進捗を復元しました", icon="♻️")
            else:
                UIStateStore.clear_active_job()
                return
        else:
            return

    active_job_id = UIStateStore.get_runtime().active_job_ids.get(run_key)
    if not active_job_id:
        return
    job = ProgressStateProxy(active_job_id)
    job.refresh()

    if hasattr(job, "refresh"):
        job.refresh()

    if not job.is_running:
        if job.error:
            toast_key = f"toasted_err_{getattr(job, 'task_id', run_key)}"
            if not UIStateStore.is_toast_notified(toast_key):
                st.toast("🚨 タスクの実行中にエラーが発生しました。", icon="🚨")
                UIStateStore.mark_toast_notified(toast_key)

            st.error(f"🚨 エラーにより停止: {job.error}")
            st.code(f"TraceID: {job.trace_id}")
            st.warning("💡 トラブルシューティング手順...", icon="⚠️")
            with st.expander("📜 エラーログを表示", expanded=True):
                st.code("\n".join(job.logs))
            if st.button("🔄 閉じる", key=f"close_err_{run_key}"):
                UIStateStore.clear_active_job()
                st.rerun()

        elif job.result_data is not None:
            toast_key = f"toasted_ok_{getattr(job, 'task_id', run_key)}"
            if not UIStateStore.is_toast_notified(toast_key):
                st.toast("✨ タスクが正常に完了しました！", icon="✨")
                UIStateStore.mark_toast_notified(toast_key)

            st.success("✨ 完了！ すべてのタスクが正常に終了しました。")

            res = job.result_data
            if isinstance(res, dict) and "book_id" in res:
                st.success(f"📖 新しい作品『{res.get('title', '無題')}』が生成されました。")
                UIStateStore.update(lambda s: setattr(s, "current_book_id", res["book_id"]), notify_keys=["current_book_id"])
                if run_key != "easy_job":
                    UIStateStore.get_runtime().app_mode = "advanced"

            if "chars_count" in res:
                st.subheader("🎉 次のステップへ進みましょう！")
                col_next1, col_next2, col_next3 = st.columns(3)
                with col_next1:
                    if render_secondary_button("詳細を微調整する", key=f"adj_{run_key}", icon=ICON_SETTINGS):
                        UIStateStore.get_runtime().app_mode = "advanced"
                        st.rerun()
                with col_next2:
                    if render_secondary_button("別の作品を生成", key=f"new_{run_key}", icon="🔄"):
                        UIStateStore.get_runtime().app_mode = "easy"
                        st.rerun()
                with col_next3:
                    if render_secondary_button("宣伝・納品を行う", key=f"promo_{run_key}", icon=ICON_PACKAGE):
                        UIStateStore.get_runtime().app_mode = "advanced"
                        st.rerun()
                st.info(f"✍️ 合計 {res['chars_count']:,} 文字を執筆しました。")

            if "failed_episodes" in res and res["failed_episodes"]:
                st.error("🚨 一部のエピソードが失敗しました。")
                if render_primary_button("失敗分を再試行", key=f"retry_{run_key}", icon="🔄"):
                    # イベント発行による再試行依頼
                    controller_manager.emit(
                        UIEventType.REQUEST_WRITE_EPISODE,
                        {
                            "book_id": res["book_id"],
                            "write_from": 1, # 実際には失敗分を特定して渡すべき
                            "write_to": 100,
                            "passion": ui_state.get_value("last_passion", 0.6),
                            "word_count": ui_state.get_value("last_word_count", 2500),
                            "do_refine": True,
                            "env_state": {},
                            "pipeline_mode": True
                        }
                    )
                    st.rerun()

            with st.expander("📜 実行詳細ログを表示"):
                st.code("\n".join(job.logs))
            if render_secondary_button("結果を確認する", key=f"confirm_{run_key}", icon="🔄", use_container_width=False):
                UIStateStore.clear_active_job()
                st.rerun()

        return

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
            st.progress(pct, text=f"全体進捗: {job.current_step}/{job.total_steps}")
        else:
            st.spinner(job.sub_message or "処理中...")

        with st.expander("🔍 リアルタイム・ログ", expanded=True):
            for log in job.logs[-5:]:
                st.caption(log)

        if render_secondary_button("処理を中断する", key=f"stop_{run_key}", icon="🛑"):
            job.stop()
            UIStateStore.clear_active_job()
            st.rerun()

    time.sleep(1.0)
    st.rerun()
