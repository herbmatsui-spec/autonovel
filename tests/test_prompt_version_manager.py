import pytest
from sqlalchemy import text

from config.project_context import GlobalConfig
from src.backend.database.uow import UnitOfWork
from src.backend.prompt_version_manager import PromptVersionManager


@pytest.mark.asyncio
async def test_prompt_version_flow():
    from config.container import Container
    db = Container.db()
    pvm = PromptVersionManager(db)

    # 既存のテーブル構造の競合を防ぐためスキーマをクリーンアップして再構築
    async with db.get_session() as session:
        async with session.begin():
            await session.execute(text("DROP TABLE IF EXISTS prompt_versions"))
            await session.execute(text("""
                CREATE TABLE prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
                    prompt_key VARCHAR,
                    version_tag VARCHAR,
                    content TEXT,
                    score_before FLOAT,
                    score_after FLOAT,
                    ab_test_metrics TEXT,
                    rollback_reason VARCHAR,
                    is_active BOOLEAN DEFAULT 0,
                    created_at VARCHAR
                )
            """))

    # 1. 最初のアクティブな本を作成
    async with UnitOfWork(db) as uow:
        book_id = await uow.books.create_book("テスト書籍", "ファンタジー", "コンセプト", "あらすじ", 10, {}, {})

    # 2. 最初期バージョンを保存
    v1_id = await pvm.save_new_version(
        book_id=book_id,
        prompt_key="optimized_prompt_patch",
        content="プロンプト ver1",
        score_before=80.0
    )
    assert v1_id is not None

    # 3. アクティブ化
    await pvm.activate_version(book_id, "optimized_prompt_patch", v1_id)
    assert GlobalConfig().get("optimized_prompt_patch") == "プロンプト ver1"

    # 4. バージョン2を保存 (スコアが85)
    v2_id = await pvm.save_new_version(
        book_id=book_id,
        prompt_key="optimized_prompt_patch",
        content="プロンプト ver2",
        score_before=85.0
    )
    await pvm.activate_version(book_id, "optimized_prompt_patch", v2_id)
    assert GlobalConfig().get("optimized_prompt_patch") == "プロンプト ver2"

    # 5. スコア評価による自動ロールバック検証 (スコアが大きく劣化した場合)
    # 85.0 -> 70.0 (劣化閾値5.0を超える)
    rolled_back = await pvm.evaluate_and_rollback_if_needed(
        book_id=book_id,
        prompt_key="optimized_prompt_patch",
        version_id=v2_id,
        score_after=70.0
    )
    assert rolled_back is True
    # v1 (健全なバージョン) に自動的に戻ることを検証
    assert GlobalConfig().get("optimized_prompt_patch") == "プロンプト ver1"

    # 後片付け
    async with UnitOfWork(db) as uow:
        await uow.books.delete_book(book_id)
