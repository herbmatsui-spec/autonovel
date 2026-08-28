"""
tests/unit/test_prototype_foreshadow.py - ステップ 7: PersistentForeshadowManager の単体テスト
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.prototype.foreshadow_adapter import PersistentForeshadowManager


@pytest.mark.asyncio
async def test_persistent_foreshadow_manager_save_and_load(tmp_path: Path):
    """モックリポジトリを用いた persist / load_persistent テスト"""
    csv_file = tmp_path / "foreshadow.csv"
    cliffs_file = tmp_path / "cliffs.txt"

    mgr1 = PersistentForeshadowManager(csv_path=csv_file, cliffs_path=cliffs_file)
    mgr1.foreshadows = [
        {"ep": 1, "type": "伏線", "text": "光の石の微かな揺らぎ", "status": "未回収"},
        {"ep": 2, "type": "伏線", "text": "謎の黒炎の痕跡", "status": "未回収"},
    ]

    mock_repo = MagicMock()
    stored_data = {}

    async def fake_save(key, val):
        stored_data[key] = val

    async def fake_get(key):
        return stored_data.get(key)

    mock_repo.save_internal_state = AsyncMock(side_effect=fake_save)
    mock_repo.get_internal_state = AsyncMock(side_effect=fake_get)

    await mgr1.persist(book_id=1, branch_id=1, repo=mock_repo)
    assert f"fs:1:1" in stored_data
    assert len(stored_data["fs:1:1"]) == 2

    # 別インスタンスで読み込み
    mgr2 = PersistentForeshadowManager(csv_path=csv_file, cliffs_path=cliffs_file)
    loaded = await mgr2.load_persistent(book_id=1, branch_id=1, repo=mock_repo)

    assert len(loaded) == 2
    assert loaded[0]["text"] == "光の石の微かな揺らぎ"
    assert mgr2.foreshadows == loaded
