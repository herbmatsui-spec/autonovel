import pytest
import threading
import time
from src.infrastructure.repositories.hook_repository import InMemoryHookRepository
from src.models.hook import Hook


def test_in_memory_hook_repository_create():
    """InMemoryHookRepository のインスタンス作成テスト"""
    repo = InMemoryHookRepository()
    assert repo is not None
    assert isinstance(repo, InMemoryHookRepository)


def test_in_memory_hook_repository_add_and_get():
    """フックの追加と取得のテスト"""
    repo = InMemoryHookRepository()
    
    # フックを作成
    hook1 = Hook(
        id="H-001",
        type="mystery",
        content="謎のフック",
        target_position="episode_end",
        volume=1,
        episode=2,
        chapter=3
    )
    
    hook2 = Hook(
        id="H-002",
        type="threat",
        content="脅威のフック",
        target_position="volume_end",
        volume=1,
        episode=5,
        chapter=2
    )
    
    # フックを追加
    repo.add(hook1)
    repo.add(hook2)
    
    # 書籍IDを計算（簡易実装に合わせる）
    book_id1 = 1 * 1000 + 2  # volume=1, episode=2 -> 1002
    book_id2 = 1 * 1000 + 5  # volume=1, episode=5 -> 1005
    
    # 取得して確認
    result1 = repo.get_by_book_id(book_id1)
    assert len(result1) == 1
    assert result1[0] == hook1
    
    result2 = repo.get_by_book_id(book_id2)
    assert len(result2) == 1
    assert result2[0] == hook2
    
    # 存在しない書籍ID
    result3 = repo.get_by_book_id(9999)
    assert len(result3) == 0


def test_in_memory_hook_repository_get_pending_hooks():
    """未使用フックの取得テスト"""
    repo = InMemoryHookRepository()
    
    # フックを作成
    hook1 = Hook(
        id="H-001",
        type="mystery",
        content="謎のフック",
        target_position="episode_end",
        volume=1,
        episode=2,
        chapter=3
    )
    
    hook2 = Hook(
        id="H-002",
        type="threat",
        content="脅威のフック",
        target_position="volume_end",
        volume=1,
        episode=5,
        chapter=2
    )
    
    # 両方を追加
    repo.add(hook1)
    repo.add(hook2)
    
    # 未使用フックを取得
    book_id1 = 1 * 1000 + 2  # volume=1, episode=2
    book_id2 = 1 * 1000 + 5  # volume=1, episode=5
    
    pending1 = repo.get_pending_hooks(book_id1)
    assert len(pending1) == 1
    assert pending1[0] == hook1
    
    pending2 = repo.get_pending_hooks(book_id2)
    assert len(pending2) == 1
    assert pending2[0] == hook2
    
    # 存在しない書籍ID
    pending3 = repo.get_pending_hooks(9999)
    assert len(pending3) == 0


def test_in_memory_hook_repository_thread_safety():
    """スレッドセーフティのテスト"""
    repo = InMemoryHookRepository()
    
    def add_hooks(start_id: int, count: int):
        """複数のフックを追加する"""
        for i in range(count):
            hook = Hook(
                id=f"H-{start_id+i:03d}",
                type="mystery",
                content=f"フック{start_id+i}",
                target_position="episode_end",
                volume=1,
                episode=1,
                chapter=1
            )
            repo.add(hook)
    
    # 複数のスレッドで同時にフックを追加
    threads = []
    for i in range(5):
        thread = threading.Thread(target=add_hooks, args=(i*100, 20))
        threads.append(thread)
        thread.start()
    
    # すべてのスレッドの終了を待つ
    for thread in threads:
        thread.join()
    
    # 総計5*20=100件のフックが追加されていることを確認
    book_id = 1 * 1000 + 1  # volume=1, episode=1
    result = repo.get_by_book_id(book_id)
    assert len(result) == 100