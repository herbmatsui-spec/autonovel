from __future__ import annotations

"""
database/repository.py - UoWコンテキストを自動解決する DataRepository ファサード
"""

from .core import DatabaseManager
from .uow_context import current_uow


class DataRepositoryFacade:
    """
    既存の engine_agents 等が `self.repo` 経由で各メソッドを呼び出せるようにするための後方互換ファサード。
    全ての呼び出しは、現在のスレッド（非同期タスク）に紐づいた UnitOfWork コンテキストを自動取得して処理を委譲します。
    もし明示的な UoW コンテキストが存在しない場合は、単一操作のために一時的な UoW コンテキストを自動生成します。
    これにより、トランザクション一元化（Phase 3）と後方互換性を両立します。

    ⚠️【アーキテクチャ設計上の注意：原則Read-Only】
    本リポジトリファサードは、クエリ（読み取り専用操作）での使用を推奨します。
    データの新規作成、更新、削除を伴う書き込み操作は、必ず明示的な `UnitOfWork` コンテキスト
    (async with UnitOfWork(db) as uow:) 内で、uow経由で行ってください。
    ファサード経由での暗黙的な自動トランザクション書き込みは推奨されません。
    """
    def __init__(self, db: DatabaseManager):
        self.db = db

    def __getattr__(self, name):
        """
        メソッド呼び出しを動的に解決する。
        各Repository（Book, Plotなど）が持つメソッドであれば、UoWが保持するそのRepositoryに委譲する。
        """
        async def wrapper(*args, **kwargs):
            uow = current_uow.get()
            if uow:
                # 既存のUoWコンテキストがある場合はそれを利用
                for repo_attr in ['books', 'plots', 'chapters', 'characters', 'branches', 'bible', 'misc', 'rules', 'audit', 'prompt_versions']:
                    repo = getattr(uow, repo_attr)
                    if hasattr(repo, name):
                         return await getattr(repo, name)(*args, **kwargs)
                raise AttributeError(f"DataRepositoryFacade (UoW mode) has no attribute '{name}'")
            else:
                # 明示的なUoWがない場合は、単発のトランザクションとしてUoWを自動生成（後方互換）
                from .uow import UnitOfWork
                async with UnitOfWork(self.db) as temp_uow:
                    for repo_attr in ['books', 'plots', 'chapters', 'characters', 'branches', 'bible', 'misc', 'rules', 'audit', 'prompt_versions']:
                        repo = getattr(temp_uow, repo_attr)
                        if hasattr(repo, name):
                             return await getattr(repo, name)(*args, **kwargs)
                    raise AttributeError(f"DataRepositoryFacade (Auto mode) has no attribute '{name}'")

        return wrapper

# DataRepository をエイリアスとして公開
DataRepository = DataRepositoryFacade

