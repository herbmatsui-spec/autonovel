"""
インメモリフックリポジトリ実装
"""

from __future__ import annotations

import threading
from typing import Dict, List

from src.domain.interfaces.hook_repository import HookRepository
from src.models.hook import Hook


class InMemoryHookRepository(HookRepository):
    """インメモリ実装のフックリポジトリ"""
    
    def __init__(self):
        """初期化"""
        # book_id -> List[Hook] のマッピング
        self._store: Dict[int, List[Hook]] = {}
        # スレッドセーフのためのロック
        self._lock = threading.RLock()
    
    def add(self, hook: Hook) -> None:
        """フックを追加する
        
        Args:
            hook: 追加するフック
        """
        with self._lock:
            # 簡易的なbook_id生成（実際は別途管理されるべき）
            book_id = hook.volume * 1000 + hook.episode
            
            if book_id not in self._store:
                self._store[book_id] = []
            
            self._store[book_id].append(hook)
    
    def get_by_book_id(self, book_id: int) -> List[Hook]:
        """書籍IDでフックを取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            該当するフックのリスト
        """
        with self._lock:
            return self._store.get(book_id, []).copy()
    
    def get_pending_hooks(self, book_id: int) -> List[Hook]:
        """未使用のフックを取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            未使用のフックのリスト
            
        Note:
            現在の実装ではすべてのフックを「未使用」として扱う。
            実際の使用状況をトラッキングする場合は、別途フラグが必要。
        """
        with self._lock:
            # 現在の実装ではすべてのフックを未使用として返す
            # 実際のアプリケーションでは、使用済みフックをマークする仕組みが必要
            return self._store.get(book_id, []).copy()