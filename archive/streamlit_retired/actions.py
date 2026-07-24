"""
streamlit_app/actions.py — UIのインタラクションからバックエンドロジックや非同期ジョブを直接起動するアクション群
"""
import os
from typing import Any, Dict

from streamlit_app.progress import run_in_background
from streamlit_app.state import UIStateStore
from streamlit_app.workflow_types import WorkflowType


def _get_run_key() -> str:
    mode = UIStateStore.get_runtime().app_mode
    return "easy_job" if mode == "easy" else "global_job"

def generate_plan(engine: Any, params: Dict[str, Any]) -> Any:
    job = run_in_background(WorkflowType.PLAN_GENERATION, params=params)
    UIStateStore.set_active_job(job, run_key=_get_run_key())
    # ウィザード状態のリセット
    UIStateStore.update(lambda s: (setattr(s.wizard, "step", 1), setattr(s.wizard, "data", {})))
    return job

def reset_wizard() -> bool:
    UIStateStore.update(lambda s: (setattr(s.wizard, "step", 1), setattr(s.wizard, "data", {})))
    return True

def write_episode(
    engine: Any,
    book_id: int,
    write_from: int,
    write_to: int,
    passion: float,
    word_count: int,
    do_refine: bool,
    env_state: Dict[str, str],
    pipeline_mode: bool
) -> Any:
    runtime = UIStateStore.get_runtime()
    runtime.last_passion = passion
    runtime.last_word_count = word_count

    job = run_in_background(
        WorkflowType.EPISODE_WRITING,
        book_id=book_id,
        write_from=write_from,
        write_to=write_to,
        passion=passion,
        word_count=word_count,
        do_refine=do_refine,
        env_state=env_state,
        pipeline_mode=pipeline_mode
    )
    UIStateStore.set_active_job(job, run_key=_get_run_key())
    return job

def expand_plot(engine: Any, book_id: int, gen_from: int, gen_to: int) -> Any:
    job = run_in_background(WorkflowType.PLOT_EXPANSION, book_id=book_id, gen_from=gen_from, gen_to=gen_to)
    UIStateStore.set_active_job(job, run_key=_get_run_key())
    return job

def rebuild_plot(engine: Any, params: Dict[str, Any]) -> Any:
    job = run_in_background(WorkflowType.PLOT_REBUILD, params=params)
    UIStateStore.set_active_job(job, run_key=_get_run_key())
    return job

def import_chapter(engine: Any, book_id: int, ep_num: int, text: str, do_refine: bool) -> Any:
    job = run_in_background(WorkflowType.IMPORT_CHAPTER, book_id=book_id, ep_num=ep_num, import_text=text, do_refine=do_refine)
    UIStateStore.set_active_job(job, run_key=_get_run_key())
    return job

def delete_chapter(engine: Any, book_id: int, ep_num: int) -> bool:
    engine.delete_chapter(book_id, ep_num)
    return True

def resolve_issue(engine: Any, issue_id: str, action: str) -> Any:
    return engine.resolve_issue(issue_id, action)

def generate_marketing_pack(engine: Any, book_id: int, last_ep: int) -> Any:
    job = run_in_background(WorkflowType.MARKETING_GENERATION, book_id=book_id, latest_ep=last_ep)
    UIStateStore.set_active_job(job, run_key=_get_run_key())
    return job

def create_export_package(engine: Any, book_id: int) -> str:
    zip_data, zip_filename = engine.marketing.create_export_package(book_id)
    temp_path = os.path.join("temp", zip_filename)
    os.makedirs("temp", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(zip_data)

    runtime = UIStateStore.get_runtime()
    runtime.download_zip_path = temp_path
    runtime.download_zip_name = zip_filename
    runtime.download_zip_data = zip_data
    return zip_filename
