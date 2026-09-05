import pytest
import threading
import time
from src.infrastructure.repositories.foreshadowing_repository import InMemoryForeshadowingRepository
from src.models.foreshadowing import Foreshadowing


def test_in_memory_foreshadowing_repository_create():
    """InMemoryForeshadowingRepository のインスタンス作成テスト"""
    repo = InMemoryForeshadowingRepository()
    assert repo is not None
    assert isinstance(repo, InMemoryForeshadowingRepository)


def test_in_memory_foreshadowing_repository_add_and_get():
    """伏線の追加と取得のテスト"""
    repo = InMemoryForeshadowingRepository()
    
    # 伏線を作成
    fs1 = Foreshadowing(
        id="F-001",
        content="主人公の秘密",
        hang_volume=1,
        hang_episode=2,
        hang_chapter=3,
        hang_type="implicit",
        importance="★★"
    )
    
    fs2 = Foreshadowing(
        id="F-002",
        content="古い遺跡",
        hang_volume=1,
        hang_episode=5,
        hang_chapter=2,
        hang_type="explicit",
        importance="★★★",
        resolution_volume=3,
        resolution_episode=1
    )
    
    # 伏線を追加
    repo.add(fs1)
    repo.add(fs2)
    
    # 書籍IDを計算（簡易実装に合わせる）
    book_id1 = 1 * 1000 + 2  # volume=1, episode=2 -> 1002
    book_id2 = 1 * 1000 + 5  # volume=1, episode=5 -> 1005
    
    # 取得して確認
    result1 = repo.get_by_book_id(book_id1)
    assert len(result1) == 1
    assert result1[0] == fs1
    
    result2 = repo.get_by_book_id(book_id2)
    assert len(result2) == 1
    assert result2[0] == fs2
    
    # 存在しない書籍ID
    result3 = repo.get_by_book_id(9999)
    assert len(result3) == 0


def test_in_memory_foreshadowing_repository_get_unresolved():
    """未解決伏線の取得テスト"""
    repo = InMemoryForeshadowingRepository()
    
    # 未解決の伏線
    fs1 = Foreshadowing(
        id="F-001",
        content="主人公の秘密",
        hang_volume=1,
        hang_episode=2,
        hang_chapter=3,
        hang_type="implicit",
        importance="★★"
    )
    
    # 解決済みの伏線
    fs2 = Foreshadowing(
        id="F-002",
        content="古い遺跡",
        hang_volume=1,
        hang_episode=5,
        hang_chapter=2,
        hang_type="explicit",
        importance="★★★",
        resolution_volume=3,
        resolution_episode=1
    )
    
    # 両方を追加
    repo.add(fs1)
    repo.add(fs2)
    
    # 未解決伏線を取得
    book_id1 = 1 * 1000 + 2  # volume=1, episode=2
    book_id2 = 1 * 1000 + 5  # volume=1, episode=5
    
    unresolved1 = repo.get_unresolved(book_id1)
    assert len(unresolved1) == 1
    assert unresolved1[0] == fs1
    
    unresolved2 = repo.get_unresolved(book_id2)
    assert len(unresolved2) == 0  # 解決済みなので空


def test_in_memory_foreshadowing_repository_resolve():
    """伏線の解決テスト"""
    repo = InMemoryForeshadowingRepository()
    
    # 未解決の伏線
    fs = Foreshadowing(
        id="F-001",
        content="主人公の秘密",
        hang_volume=1,
        hang_episode=2,
        hang_chapter=3,
        hang_type="implicit",
        importance="★★"
    )
    
    # 追加
    repo.add(fs)
    
    # 解決前は未解決
    book_id = 1 * 1000 + 2  # volume=1, episode=2
    unresolved_before = repo.get_unresolved(book_id)
    assert len(unresolved_before) == 1
    
    # 解決を実行
    repo.resolve("F-001", 3, 1)  # 第3巻第1話で解決
    
    # 解決後は解決済み
    unresolved_after = repo.get_unresolved(book_id)
    assert len(unresolved_after) == 0
    
    # 解決情報が正しく設定されているか確認
    result = repo.get_by_book_id(book_id)
    assert len(result) == 1
    assert result[0].resolution_volume == 3
    assert result[0].resolution_episode == 1


def test_in_memory_foreshadowing_repository_get_balance():
    """伏線バランスの取得テスト"""
    repo = InMemoryForeshadowingRepository()
    
    # 巻1の伏線をいくつか追加
    fs1 = Foreshadowing(
        id="F-001",
        content="伏線1",
        hang_volume=1,
        hang_episode=1,
        hang_chapter=1,
        hang_type="implicit",
        importance="★"
    )
    
    fs2 = Foreshadowing(
        id="F-002",
        content="伏線2",
        hang_volume=1,
        hang_episode=2,
        hang_chapter=2,
        hang_type="explicit",
        importance="★★",
        resolution_volume=1,  # 巻1で解決
        resolution_episode=3
    )
    
    fs3 = Foreshadowing(
        id="F-003",
        content="伏線3",
        hang_volume=1,
        hang_episode=3,
        hang_chapter=3,
        hang_type="reader_task",
        importance="★★★"
    )
    
    # 巻2の伏線
    fs4 = Foreshadowing(
        id="F-004",
        content="巻2の伏線",
        hang_volume=2,
        hang_episode=1,
        hang_chapter=1,
        hang_type="implicit",
        importance="★"
    )
    
    repo.add(fs1)
    repo.add(fs2)
    repo.add(fs3)
    repo.add(fs4)
    
    # 巻1のバランスを取得
    # hang_count: 3 (fs1, fs2, fs3)
    # resolve_count: 1 (fs2のみ解決済み)
    # balance: 3 - 1 = 2
    balance1 = repo.get_balance(1)
    assert balance1["hang_count"] == 3
    assert balance1["resolve_count"] == 1
    assert balance1["balance"] == 2
    
    # 巻2のバランスを取得
    # hang_count: 1 (fs4)
    # resolve_count: 0 (未解決)
    # balance: 1 - 0 = 1
    balance2 = repo.get_balance(2)
    assert balance2["hang_count"] == 1
    assert balance2["resolve_count"] == 0
    assert balance2["balance"] == 1
    
    # 巻3のバランスを取得（伏線なし）
    balance3 = repo.get_balance(3)
    assert balance3["hang_count"] == 0
    assert balance3["resolve_count"] == 0
    assert balance3["balance"] == 0


def test_in_memory_foreshadowing_repository_thread_safety():
    """スレッドセーフティのテスト"""
    repo = InMemoryForeshadowingRepository()
    
    def add_foreshadowings(start_id: int, count: int):
        """複数の伏線を追加する"""
        for i in range(count):
            fs = Foreshadowing(
                id=f"F-{start_id+i:03d}",
                content=f"伏線{start_id+i}",
                hang_volume=1,
                hang_episode=1,
                hang_chapter=1,
                hang_type="implicit",
                importance="★"
            )
            repo.add(fs)
    
    # 複数のスレッドで同時に伏線を追加
    threads = []
    for i in range(5):
        thread = threading.Thread(target=add_foreshadowings, args=(i*100, 20))
        threads.append(thread)
        thread.start()
    
    # すべてのスレッドの終了を待つ
    for thread in threads:
        thread.join()
    
    # 総計5*20=100件の伏線が追加されていることを確認
    book_id = 1 * 1000 + 1  # volume=1, episode=1
    result = repo.get_by_book_id(book_id)
    assert len(result) == 100