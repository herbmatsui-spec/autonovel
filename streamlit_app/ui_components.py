import logging
import time
from typing import Any, List, Optional, TypedDict

import streamlit as st

from streamlit_app.state import UIStateStore
from streamlit_app.workflow_types import WorkflowType

logger = logging.getLogger(__name__)

COST_INPUT_FLASH = 0.00000025
COST_OUTPUT_FLASH = 0.0000015

PROGRESS_POLL_INTERVAL_SEC = 2.0
MAX_BACKOFF_SEC = 30
JOB_REFRESH_TIMEOUT_SEC = 5.0

class EasyParameters(TypedDict, total=False):
    cheat_scale: int
    system_assist: int
    cost_severity: int
    concept: str

class FailedEpisode(TypedDict, total=False):
    ep_num: int
    error_message: str

class JobResult(TypedDict, total=False):
    easy_parameters: EasyParameters
    chars_count: int
    failed_episodes: List[FailedEpisode]
    book_id: int


def inject_focus_css() -> None:
    """入力フィールドのフォーカス維持のためのCSSを注入 (session_stateを用いて一度だけ)"""
    from streamlit_app.state_keys import CSS_INJECTED_KEY
    if not UIStateStore().ui_state.form_data.get(CSS_INJECTED_KEY, False):
            </style> -->
        """, unsafe_allow_html=True)
        UIStateStore().update_ui_state(CSS_INJECTED_KEY=True)

def display_token_cost(text: str, label: str = "内容") -> None:
    """トークンコストを表示する共通ウィジェット"""
    with st.container():
        st.markdown(f"**{label}**: {text}")

_PHASE_HTML_TEMPLATE = (
    "<div style='background-color: {bg_color}; color: {color}; padding: 10px 5px; "
    "border-radius: 6px; text-align: center; font-weight: {font_weight}; "
    "border: {border}; box-shadow: {box_shadow}; font-size: 0.85em;'>"
    "{prefix} {name}"
    "</div>"
)

_PHASE_STYLES = {
    "active": {
        "bg_color": "#0f766e", "color": "white", "font_weight": "bold",
        "border": "1.5px solid #14b8a6", "box_shadow": "0 0 10px rgba(20, 184, 166, 0.4)", "prefix": "🔥"
    },
    "completed": {
        "bg_color": "rgba(6, 95, 70, 0.2)", "color": "#34d399", "font_weight": "500",
        "border": "1px solid rgba(52, 211, 153, 0.4)", "box_shadow": "none", "prefix": "✅"
    },
    "pending": {
        "bg_color": "rgba(255, 255, 255, 0.02)", "color": "#6b7280", "font_weight": "normal",
        "border": "1px dashed rgba(107, 114, 128, 0.3)", "box_shadow": "none", "prefix": "💤"
    }
}

def render_production_dashboard(job: Any) -> None:
    wf_type = getattr(job, "workflow_type", None)
    if not wf_type:
        return

    phases = [
        ("📋 企画立案", [WorkflowType.PLAN_GENERATION]),
        ("📖 プロット構成", [WorkflowType.PLOT_EXPANSION, WorkflowType.PLOT_REBUILD]),
        ("✍️ 本文執筆", [WorkflowType.EPISODE_WRITING, WorkflowType.IMPORT_CHAPTER, WorkflowType.RETRY_FAILED]),
        ("⚖️ 推敲・最適化", [WorkflowType.CRITIQUE_OPTIMIZE]),
        ("📢 宣伝・納品", [WorkflowType.MARKETING_GENERATION]),
    ]

    active_idx = -1
    if wf_type == WorkflowType.FULL_AUTO:
        curr = getattr(job, "current_step", 1)
        if curr <= 1:
            active_idx = 0
        elif curr == 2:
            active_idx = 1
        else:
            active_idx = 2
    else:
        for idx, (_, wfs) in enumerate(phases):
            if wf_type in wfs:
                active_idx = idx
                break

    cols = st.columns(len(phases))
    for idx, (name, _) in enumerate(phases):
        with cols[idx]:
            if idx == active_idx:
                style_key = "active"
            elif idx < active_idx:
                style_key = "completed"
            else:
                style_key = "pending"
            style = _PHASE_STYLES[style_key]
            st.markdown(_PHASE_HTML_TEMPLATE.format(name=name, **style), unsafe_allow_html=True)

def _should_skip_poll(run_key: str) -> bool:
    if UIStateStore.is_processing():
        return True
    fail_count = UIStateStore.get_poll_fail_count(run_key)
    if fail_count > 0:
        skip_until = UIStateStore.get_poll_skip_until(run_key)
        if time.time() < skip_until:
            return True
    return False

def _refresh_job_status(job: Any, run_key: str) -> bool:
    try:
        job.refresh(timeout=JOB_REFRESH_TIMEOUT_SEC)
        UIStateStore.reset_poll_fail_count(run_key)
        return True
    except Exception:
        UIStateStore.increment_poll_fail_count(run_key)
        new_fail_count = UIStateStore.get_poll_fail_count(run_key)
        UIStateStore.set_poll_skip_until(run_key, time.time() + min(2**new_fail_count, MAX_BACKOFF_SEC))
        st.warning(f"📡 通信不安定です... 再試行中 ({new_fail_count})")

@st.fragment(run_every=PROGRESS_POLL_INTERVAL_SEC)
def progress_dispatcher(run_key: str):
    if _should_skip_poll(run_key):
        return
    job = UIStateStore.get_monitored_jobs().get(run_key)
    if not job:
        return
    has_changed = job.refresh(timeout=JOB_REFRESH_TIMEOUT_SEC)
    if has_changed:
        UIStateStore.bump_fragment_version("status")
        current_logs_ver = UIStateStore().ui_state.form_data.get("logs_version", 0)
        if current_logs_ver != len(job.logs):
            UIStateStore().update_ui_state(logs_version=len(job.logs))
            UIStateStore.bump_fragment_version("logs")

@st.fragment
def status_display_fragment(run_key: str, engine: Any = None):
    version = UIStateStore.get_fragment_version("status")
    last_drawn = UIStateStore().ui_state.form_data.get("last_drawn_status")
    if last_drawn == version:
        return
    UIStateStore().update_ui_state(last_drawn_status=version)
    job = UIStateStore.get_monitored_jobs().get(run_key)
    if not job:
        return
    render_production_dashboard(job)
    if job.is_running:
        _render_job_running(st.container(), job, run_key)
    else:
        _render_job_completed(st.container(), job, run_key, engine)

def progress_fragment(run_key: str, engine: Optional[Any] = None) -> None:
    progress_dispatcher(run_key)
    status_display_fragment(run_key, engine)
    job = UIStateStore.get_monitored_jobs().get(run_key)
    if job:
        log_fragment(job.logs, run_key)

def _set_current_tab(tab_name: str) -> None:
    try:
        UIStateStore.update_runtime("current_tab", tab_name)
    except AttributeError:
        setattr(UIStateStore.get_runtime(), "current_tab", tab_name)

def trigger_app_rerun() -> None:
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()

@st.fragment
def next_steps_fragment(res: JobResult, run_key: str) -> None:
    from streamlit_app.ui.components.widgets import render_primary_button

    with st.container(border=True):
        st.markdown("### 🎉 企画が完了しました！")
        st.markdown("この企画をベースに、次のステップへ進みましょう。")

        if run_key == "easy_job":
            col1, col2, col3 = st.columns(3)
            with col1:
                if render_primary_button("📝 詳細編集へ", key=f"next_edit_{run_key}", icon="✍️"):
                    _set_current_tab("writing")
                    UIStateStore.clear_active_job(run_key)
                    trigger_app_rerun()
            with col2:
                if render_primary_button("🧐 プロット監査", key=f"next_audit_{run_key}", icon="🔍"):
                    _set_current_tab("analytics")
                    UIStateStore.clear_active_job(run_key)
                    trigger_app_rerun()
            with col3:
                if render_primary_button("📖 全体確認", key=f"next_view_{run_key}", icon="📚"):
                    _set_current_tab("viewer")
                    UIStateStore.clear_active_job(run_key)
                    trigger_app_rerun()
        else:
            if render_primary_button("✅ 完了して戻る", key=f"next_done_{run_key}", icon="🏁"):
                UIStateStore.clear_active_job(run_key)
                trigger_app_rerun()

@st.fragment
def log_fragment(logs: List[str], run_key: str) -> None:
    idx_key = f"_last_log_idx_{run_key}"
    last_idx = UIStateStore().ui_state.form_data.get(idx_key, 0)
    with st.expander("📜 実行詳細ログを表示", expanded=True):
        if not logs:
            st.caption("ログはまだありません。")
            return
        if last_idx == 0:
            from streamlit_app.state_keys import LOG_INDEX_PREFIX
            st.code("\n".join(logs), language="text")
            UIStateStore().update_ui_state(**{f"{LOG_INDEX_PREFIX}{idx_key}": len(logs)})
        else:
            if len(logs) > last_idx:
                new_logs = "\n".join(logs[last_idx:])
                from streamlit_app.state_keys import LOG_INDEX_PREFIX
                st.text(new_logs)
                UIStateStore().update_ui_state(**{f"{LOG_INDEX_PREFIX}{idx_key}": len(logs)})

@st.fragment
def token_usage_fragment(job: Any) -> None:
    """トークン使用量を表示するフラグメント"""
    usage = getattr(job, "token_usage", {})
    if usage:
        with st.container():
            st.metric("トークン使用量", f"{usage['prompt']} prompt, {usage['completion']} completion, {usage['calls']} calls")
            st.caption(f"推定コスト: ${usage['prompt'] * COST_INPUT_FLASH + usage['completion'] * COST_OUTPUT_FLASH:.6f}")

def _render_job_running(container, job, run_key):
    with container:
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
        if st.button("🛑 処理を中断する", key=f"stop_{run_key}", type="secondary"):
            job.stop()
            UIStateStore.clear_active_job()
            st.rerun()


def _render_job_completed(container, job, run_key, engine):
    if job.error:
        toast_key = f"toasted_err_{getattr(job, 'task_id', run_key)}"
        if not UIStateStore.is_toast_notified(toast_key):
            st.toast("🚨 タスクの実行中にエラーが発生しました。", icon="🚨")
            UIStateStore.mark_toast_notified(toast_key)
        st.error(f"🚨 エラーにより停止: {job.error}")
        st.code(f"TraceID: {job.trace_id}")
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
            st.info(f"✍️ 合計 {res['chars_count']:,} 文字を執筆しました。")
        with st.expander("📜 実行詳細ログを表示"):
            st.code("\n".join(job.logs))
        if st.button("🔄 結果を確認する", key=f"confirm_{run_key}"):
            UIStateStore.clear_active_job()
            st.rerun()
