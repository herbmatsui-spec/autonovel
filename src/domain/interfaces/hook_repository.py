"""
フックリポジトリインターフェース
"""

from __future__ import annotations

from typing import List

from src.models.hook import Hook


class HookRepository:
    """フックデータのリポジトリインターフェース"""
    
    def add(self, hook: Hook) -> None:
        """フックを追加する
        
        Args:
            hook: 追加するフック
        """
        raise NotImplementedError()
    
    def get_by_book_id(self, book_id: int) -> List[Hook]:
        """書籍IDでフックを取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            該当するフックのリスト
        """
        raise NotImplementedError()
    
    def get_pending_hooks(self, book_id: int) -> List[Hook]:
        """未使用のフックを取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            未使用のフックのリスト
        """
        raise NotImplementedError()