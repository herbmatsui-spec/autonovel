"""
インメモリ伏線リポジトリ実装
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from src.domain.interfaces.foreshadowing_repository import ForeshadowingRepository
from src.models.foreshadowing import Foreshadowing


class InMemoryForeshadowingRepository(ForeshadowingRepository):
    """インメモリ実装の伏線リポジトリ"""
    
    def __init__(self):
        """初期化"""
        # book_id -> List[Foreshadowing] のマッピング
        self._store: Dict[int, List[Foreshadowing]] = {}
        # スレッドセーフのためのロック
        self._lock = threading.RLock()
        # 伏線IDの連番管理のためのカウンター
        # (genre, volume, episode) -> 次に使う連番
        self._id_counter: Dict[tuple, int] = {}
    
    def add(self, foreshadowing: Foreshadowing) -> None:
        """伏線を追加する
        
        Args:
            foreshadowing: 追加する伏線
        """
        with self._lock:
            book_id = foreshadowing.hang_volume * 1000 + foreshadowing.hang_episode  # 簡易的なbook_id生成
            # 実際の実装では、book_id は別途管理されるべきだが、
            # ここでは簡易的に巻数と話数から生成
            
            if book_id not in self._store:
                self._store[book_id] = []
            
            self._store[book_id].append(foreshadowing)
    
    def get_by_book_id(self, book_id: int) -> List[Foreshadowing]:
        """書籍IDで伏線を取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            該当する伏線のリスト
        """
        with self._lock:
            return self._store.get(book_id, []).copy()
    
    def get_unresolved(self, book_id: int) -> List[Foreshadowing]:
        """未解決の伏線を取得する
        
        Args:
            book_id: 書籍ID
            
        Returns:
            未解決の伏線のリスト
        """
        with self._lock:
            foreshadowings = self._store.get(book_id, [])
            unresolved = [
                fs for fs in foreshadowings
                if fs.resolution_volume is None and fs.resolution_episode is None
            ]
            return unresolved.copy()
    
    def resolve(self, foreshadowing_id: str, volume: int, episode: int) -> None:
        """伏線を解決済みとしてマークする
        
        Args:
            foreshadowing_id: 伏線ID
            volume: 解決巻数
            episode: 解決話数
        """
        with self._lock:
            # すべての書籍を検索して該当する伏線を見つける
            for book_id, foreshadowings in self._store.items():
                for fs in foreshadowings:
                    if fs.id == foreshadowing_id:
                        # 解決情報を更新
                        fs.resolution_volume = volume
                        fs.resolution_episode = episode
                        return
    
    def get_balance(self, volume: int) -> dict:
        """巻ごとの伏線バランスを取得する
        
        Args:
            volume: 巻数
            
        Returns:
            バランス情報を含む辞書
            例: {"hang_count": int, "resolve_count": int, "balance": int}
        """
        with self._lock:
            hang_count = 0
            resolve_count = 0
            
            # すべての書籍を検索
            for foreshadowings in self._store.values():
                for fs in foreshadowings:
                    if fs.hang_volume == volume:
                        hang_count += 1
                        if fs.resolution_volume is not None and fs.resolution_episode is not None:
                            resolve_count += 1
            
            balance = hang_count - resolve_count
            
            return {
                "hang_count": hang_count,
                "resolve_count": resolve_count,
                "balance": balance
            }