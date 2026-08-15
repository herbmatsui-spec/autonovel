"""
tests/integration/test_trace.py

機能7（生成ログ・Trace ID 再現性レポート）の統合テスト。
実行記録の保存・取得・報告書生成、および同一入力でのハッシュ一致を検証する。
"""
import pytest

from src.services.reproducibility import build_report, build_run_record, compute_input_hash


def test_compute_input_hash_is_stable():
    a = compute_input_hash({"x": 1, "y": [1, 2]})
    b = compute_input_hash({"y": [1, 2], "x": 1})
    assert a == b
    assert len(a) == 64


def test_build_run_record_has_hash():
    rec = build_run_record(
        book_id=1, task_type="writing", prompt_version="v1",
        model_name="gemini-pro", params={"temp": 0.7},
        payload={"book_id": 1, "ep": 3}, output_preview="本文",
    )
    assert rec["input_hash"]
    assert rec["params_json"] == '{"temp": 0.7}'


def test_build_report_contains_runs():
    rec = build_run_record(
        book_id=1, task_type="writing", prompt_version="v1",
        model_name="gemini-pro", params={}, payload={}, output_preview="x",
    )
    report = build_report([rec])
    assert report["count"] == 1
    assert "生成再現性レポート" in report["markdown"]
    assert "gemini-pro" in report["markdown"]


@pytest.mark.asyncio
async def test_trace_repository_lifecycle(real_uow):
    """GenerationRun の記録・取得・報告書生成を確認。"""
    from config.container import Container

    async with real_uow as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})
        Container.db = lambda: real_uow.db

    from src.backend.routers import trace as trace_router

    res = await trace_router.record_run(
        book_id,
        trace_router.RunRequest(task_type="writing", prompt_version="v1",
                                 model_name="gemini-pro", params={"temp": 0.7},
                                 payload={"ep": 1}, trace_id="abc123", chapter_ep=1),
    )
    assert res["status"] == "success"
    assert res["input_hash"]

    runs = await trace_router.list_runs(book_id, chapter_ep=None)
    assert len(runs) == 1

    report = await trace_router.reproducibility_report(book_id, chapter_ep=None)
    assert report["count"] == 1
    assert "abc123" in report["markdown"]
