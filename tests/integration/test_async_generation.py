"""Generation task persistence and cleanup integration test.

Step 31 補完として、Huey タスク ``generate_chapter_task`` が正常終了した際に
DB 上の ``Task`` レコードへ結果を保存した後、そのレコードを削除する
クリーンアップ挙動を検証する。

本テストは同期関数として定義し、``_run_async`` が新規イベントループを
安全に作成できるようにする (pytest-asyncio のループと競合させない)。
``generate_with_llm`` は未実装のため monkeypatch でダミー戻り値に差し替える。
"""
from __future__ import annotations

import asyncio

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.tasks import generation_tasks
from src.backend.tasks.generation_tasks import generate_chapter_task


def test_generation_task_persists_and_cleans_up(real_db_manager, monkeypatch) -> None:
    """生成タスクは DB へ結果を保存したのち、タスクレコードを削除する。"""
    # real_db_manager が差し替えた engine 上でセッションを取得
    repo = BookRepository(real_db_manager)

    # タスクレコードを事前に作成して ID を採番
    loop = asyncio.new_event_loop()
    try:
        task = loop.run_until_complete(repo.create_task())
    finally:
        loop.close()
    task_id = task.id

    # LLM 未実装のため、成功ルートを強制するダミーに差し替え
    async def _fake_generate(payload):  # type: ignore[no-untyped-def]
        return {"text": "ダミー生成テキスト", "time": 10}

    monkeypatch.setattr(generation_tasks, "_generate", _fake_generate)

    # タスク関数へ渡す payload (task_id 含む)
    payload = {
        "task_id": task_id,
        "chapter_history": [],
        "current_chapter": "テスト章",
        "character": {},
    }

    # Huey の call_local は装飾を通さず生の戻り値を返す
    result = generate_chapter_task.call_local(payload)
    # Result ラッパーで包まれる場合もあるため安全にアンラップ
    if hasattr(result, "get") and callable(getattr(result, "get")):
        try:
            result = result.get()  # type: ignore[call-arg]
        except TypeError:
            # dict.get など引数を要求する場合は生戻り値とみなす
            pass
    assert isinstance(result, dict)
    assert "text" in result

    # クリーンアップ後、タスクレコードが削除されていることを検証。
    # タスク関数内部で別セッションが削除を commit するため、検証には
    # identity map の影響を受けないよう新規セッションを使用する。
    verify_session = database.SessionLocal()
    try:
        verify_repo = BookRepository(verify_session)
        loop = asyncio.new_event_loop()
        try:
            deleted = loop.run_until_complete(verify_repo.get_task(task_id))
        finally:
            loop.close()
    finally:
        verify_session.close()
    assert deleted is None, "Task record should be cleaned up after result persistence"
