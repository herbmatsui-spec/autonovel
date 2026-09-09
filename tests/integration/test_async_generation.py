"""Generation task persistence and cleanup integration test.

Step 31 補完として、Huey タスク ``generate_chapter_task`` が正常終了した際に
DB 上の ``Task`` レコードへ結果を保存した後、そのレコードを削除する
クリーンアップ挙動を検証する。

本テストは同期関数として定義し、``_run_async`` が新規イベントループを
安全に作成できるようにする (pytest-asyncio のループと競合させない)。
``generate_with_llm`` は未実装のため monkeypatch でダミー戻り値に差し替える。
"""
from __future__ import annotations

from src.backend import database
from src.backend.database.models import Book, Chapter, Character
from src.backend.database.repository import BookRepository
from src.backend.tasks import generation_tasks
from src.backend.tasks.generation_tasks import generate_chapter_task
from sqlalchemy import select


def test_generation_task_persists_and_cleans_up(real_db_manager, monkeypatch) -> None:
    """生成タスクは DB へ結果を保存する。"""
    # real_db_manager が差し替えた engine 上でセッションを取得
    repo = BookRepository(real_db_manager)

    # タスクレコードを事前に作成して ID を採番
    task = repo.create_task()
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

    # 結果保存後、タスクレコードが completed になっていることを検証
    verify_session = database.SessionLocal()
    try:
        verify_repo = BookRepository(verify_session)
        persisted_task = verify_repo.get_task(task_id)
        assert persisted_task is not None
        assert persisted_task.status == "completed"
        assert persisted_task.result is not None
        assert "ダミー生成テキスト" in persisted_task.result
    finally:
        verify_session.close()


def test_generation_task_saves_to_specified_book_id(real_db_manager, monkeypatch) -> None:
    """指定した book_id の Book / Chapter にデータが保存されることを検証"""
    # real_db_manager が差し替えた engine 上でセッションを取得
    repo = BookRepository(real_db_manager)

    # 指定した book_id の本を事前に作成しておく
    specified_book_id = 999
    book = Book(
        id=specified_book_id,
        title="元のタイトル",
        genre="元のジャンル",
        concept="元のコンセプト",
        synopsis="元のあらすじ",
        target_eps=10,
    )
    repo.session.add(book)
    repo._safe_commit()
    repo._safe_refresh(book)

    # タスクレコードを事前に作成して ID を採番
    task = repo.create_task()
    task_id = task.id

    # LLM 未実装のため、成功ルートを強制するダミーに差し替え
    async def _fake_generate(payload):  # type: ignore[no-untyped-def]
        return {"text": "生成された章のテキスト", "time": 10}

    monkeypatch.setattr(generation_tasks, "_generate", _fake_generate)

    # タスク関数へ渡す payload (task_id と book_id を含む)
    payload = {
        "task_id": task_id,
        "chapter_history": [],
        "current_chapter": "現在の章テキスト",
        "character": {"name": "テスト主人公", "personality": "勇敢", "ability": "剣術", "genre": "ファンタジー"},
        "book_id": specified_book_id,
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

    # 結果保存後、タスクレコードが completed になっていることを検証
    verify_session = database.SessionLocal()
    try:
        verify_repo = BookRepository(verify_session)
        persisted_task = verify_repo.get_task(task_id)
        assert persisted_task is not None
        assert persisted_task.status == "completed"
        assert persisted_task.result is not None
        assert "生成された章のテキスト" in persisted_task.result

        # 指定した book_id の本が更新されていることを検証
        updated_book = verify_repo.get_book(specified_book_id)
        assert updated_book is not None
        assert updated_book.title == "テスト主人公の冒険譚"  # 生成されたタイトル
        assert updated_book.genre == "ファンタジー"  # キャラクターのジャンルから更新される
        # 第1話が更新されていることを検証
        from sqlalchemy import select
        stmt = select(Chapter).where(Chapter.book_id == specified_book_id).where(Chapter.ep_num == 1)
        chapter = verify_repo.session.execute(stmt).scalar_one_or_none()
        assert chapter is not None
        assert chapter.content == "生成された章のテキスト"
        assert chapter.summary == "生成された章のテキスト"[:100]
        # キャラクターが更新されていることを検証
        stmt = select(Character).where(Character.book_id == specified_book_id).where(Character.name == "テスト主人公")
        character = verify_repo.session.execute(stmt).scalar_one_or_none()
        assert character is not None
        assert character.personality == "勇敢"
        assert character.ability == "剣術"
    finally:
        verify_session.close()


def test_generation_task_creates_new_book_when_book_id_not_provided(real_db_manager, monkeypatch) -> None:
    """book_id が指定されない場合、新しい作品が作成され、既存の book_id=1 が無傷のままであることを検証"""
    # real_db_manager が差し替えた engine 上でセッションを取得
    repo = BookRepository(real_db_manager)

    # 既存の book_id=1 の本を作成しておく
    existing_book = Book(
        id=1,
        title="既存のタイトル",
        genre="既存のジャンル",
        concept="既存のコンセプト",
        synopsis="既存のあらすじ",
        target_eps=10,
    )
    repo.session.add(existing_book)
    repo._safe_commit()
    repo._safe_refresh(existing_book)

    # タスクレコードを事前に作成して ID を採番
    task = repo.create_task()
    task_id = task.id

    # LLM 未実装のため、成功ルートを強制するダミーに差し替え
    async def _fake_generate(payload):  # type: ignore[no-untyped-def]
        return {"text": "生成された章のテキスト", "time": 10}

    monkeypatch.setattr(generation_tasks, "_generate", _fake_generate)

    # タスク関数へ渡す payload (task_id 含む、book_id は含まない)
    payload = {
        "task_id": task_id,
        "chapter_history": [],
        "current_chapter": "現在の章テキスト",
        "character": {"name": "新規主人公", "personality": "賢い", "ability": "魔法", "genre": "ファンタジー"},
        # book_id は指定しない
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

    # 結果保存後、タスクレコードが completed になっていることを検証
    verify_session = database.SessionLocal()
    try:
        verify_repo = BookRepository(verify_session)
        persisted_task = verify_repo.get_task(task_id)
        assert persisted_task is not None
        assert persisted_task.status == "completed"
        assert persisted_task.result is not None
        assert "生成された章のテキスト" in persisted_task.result

        # タスク結果から生成された book_id を取得することを検証
        # (Step 14: タスク結果 JSON に保存先 book_id を自動注入)
        import json
        result_dict = json.loads(persisted_task.result)
        assert "book_id" in result_dict
        new_book_id = result_dict["book_id"]
        assert isinstance(new_book_id, int)
        assert new_book_id > 0
        assert new_book_id != 1  # 新しい ID であることを確認

        # 新しい本が作成されていることを検証
        new_book = verify_repo.get_book(new_book_id)
        assert new_book is not None
        assert new_book.title == "新規主人公の冒険譚"
        assert new_book.genre == "ファンタジー"
        # 第1話が作成されていることを検証
        from sqlalchemy import select
        stmt = select(Chapter).where(Chapter.book_id == new_book_id).where(Chapter.ep_num == 1)
        chapter = verify_repo.session.execute(stmt).scalar_one_or_none()
        assert chapter is not None
        assert chapter.content == "生成された章のテキスト"
        assert chapter.summary == "生成された章のテキスト"[:100]
        # キャラクターが作成されていることを検証
        stmt = select(Character).where(Character.book_id == new_book_id).where(Character.name == "新規主人公")
        character = verify_repo.session.execute(stmt).scalar_one_or_none()
        assert character is not None
        assert character.personality == "賢い"
        assert character.ability == "魔法"

        # 既存の book_id=1 の本が無傷であることを検証
        unchanged_book = verify_repo.get_book(1)
        assert unchanged_book is not None
        assert unchanged_book.title == "既存のタイトル"
        assert unchanged_book.genre == "既存のジャンル"
        # 第1話が変更されていないことを検証
        stmt = select(Chapter).where(Chapter.book_id == 1).where(Chapter.ep_num == 1)
        chapter = verify_repo.session.execute(stmt).scalar_one_or_none()
        assert chapter is not None
        assert chapter.content == ""  # 元は空だったはず
        assert chapter.summary == ""  # 元は空だったはず
        # キャラクターが変更されていないことを検証
        stmt = select(Character).where(Character.book_id == 1).where(Character.name == "")  # 元は空だったはず
        character = verify_repo.session.execute(stmt).scalar_one_or_none()
        # 既存の本にキャラクターが登録されていないことを確認
        assert character is None
    finally:
        verify_session.close()
