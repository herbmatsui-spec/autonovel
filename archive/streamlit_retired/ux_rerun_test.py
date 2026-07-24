"""
ux_rerun_test.py — Rerun UX テストページ（テスト用スクリプト）

注意: 本ファイルはテスト用途のため、st.session_state は MockJob 保持にのみ使用。
実際のアプリコードでは UIStateStore 経由で状態管理してください。
"""
from typing import Any

import streamlit as st

from streamlit_app.state import UIStateStore


# Mock Job object to simulate background process
class MockJob:
    def __init__(self):
        self.is_running = True
        self.message = "Processing..."
        self.sub_message = "Step 1/10"
        self.current_step = 1
        self.total_steps = 10
        self.start_time = time.time()
        self.logs = ["Starting job..."]
        self.streaming_text = ""
        self.token_usage = {"prompt": 0, "completion": 0, "calls": 0}
        self.error = None
        self.result_data = None

    def refresh(self):
        if self.current_step < self.total_steps:
            self.current_step += 1
            self.sub_message = f"Step {self.current_step}/{self.total_steps}"
            self.logs.append(f"Completed step {self.current_step}")
        else:
            self.is_running = False
            self.result_data = {"status": "success", "book_id": "test_123"}

    def stop(self):
        self.is_running = False


# Fragment under test
@st.fragment
def progress_fragment(run_key: str, job: Any):
    st.write(f"--- Fragment: {run_key} ---")
    job.refresh()

    if job.is_running:
        st.write(f"Status: {job.message} - {job.sub_message}")
        st.progress(job.current_step / job.total_steps)
        st.write("Logs:")
        for log in job.logs[-3:]:
            st.caption(log)

        st.rerun()
    else:
        st.success("Job Finished!")


# Main App
st.title("Rerun UX Test Page")

# Input that should NOT be reset
st.subheader("Input Area (Check if this resets)")
user_input = st.text_area("Type something here while job runs...", key="test_input")
st.write(f"Current input value: {user_input}")

# テスト用: UIStateStore 経由でジョブ状態を管理
job = UIStateStore.get_runtime().monitored_jobs.get("test_job_key")
if job is None:
    mock = MockJob()
    UIStateStore.set_active_job(mock, run_key="test_job_key")
    job = mock

# Call the fragment
progress_fragment("test_job_key", job)

if st.button("Reset Job"):
    UIStateStore.set_active_job(MockJob(), run_key="test_job_key")
    st.rerun()

st.info("Observe: If the text area loses focus or the text disappears/flickers when the progress bar updates, the fragment is triggering a full rerun.")
