"""
伏線リポジトリインターフェース
"""

from __future__ import annotations

from typing import List, Optional

from src.models.foreshadowing import Foreshadowing


class ForeshadowingRepository:
    """伏線データのリポジトリインターフェース"""
    
    def add(self, foreshadowing: Foreshadowing) -> None:
        """伏線を追加する
        
        Args:
            foreshadowing: 追加する伏線
        """
        raise NotImplementedError()
    
    def get_by_book_id(self, book_id: int) -> List[Foreshadowing]:
        """書籍IDで伏線を取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            該当する伏線のリスト
        """
        raise NotImplementedError()
    
    def get_unresolved(self, book_id: int) -> List[Foreshadowing]:
        """未解決の伏線を取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            未解決の伏線のリスト
        """
        raise NotImplementedError()
    
    def resolve(self, foreshadowing_id: str, volume: int, episode: int) -> None:
        """伏線を解決済みとしてマークする
        
        Args:
            foreshadowing_id: 伏線ID
            volume: 解決巻数
            episode: 解決話数
        """
        raise NotImplementedError()
    
    def get_balance(self, volume: int) -> dict:
        """巻ごとの伏線バランスを取得する
        
        Args:
            volume: 巻数
            
        Returns:
            バランス情報を含む辞書
            例: {"hang_count": int, "resolve_count": int, "balance": int}
        """
        raise NotImplementedError()