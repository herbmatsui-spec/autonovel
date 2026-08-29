from __future__ import annotations

"""
database/repositories/story_canvas_repo.py - ストーリーキャンバス用リポジトリ
"""
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import delete, select, update

from src.backend.database.models import StoryEdge, StoryNode
from src.services.errors import retry_on_lock

if TYPE_CHECKING:
    from src.models.api_schemas import StoryCanvasResponse, StoryNodeSchema, StoryEdgeSchema

from src.backend.database.repositories.base import BaseRepository


class StoryCanvasRepository(BaseRepository):
    """StoryNode / StoryEdge テーブルに関する DB 操作"""

    def _parse_data(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {}
        return value or {}

    async def get_nodes(self, book_id: int) -> List["StoryNodeSchema"]:
        result = await self.session.execute(
            select(StoryNode).where(StoryNode.book_id == book_id).order_by(StoryNode.id)
        )
        rows = result.scalars().all()
        from src.models.api_schemas import StoryNodeSchema

        return [
            StoryNodeSchema(
                id=f"node-{row.id}",
                book_id=row.book_id,
                kind=row.kind,
                label=row.label,
                ep_num=row.ep_num,
                character_id=row.character_id,
                x=row.x or 0.0,
                y=row.y or 0.0,
                data=self._parse_data(row.data),
            )
            for row in rows
        ]

    async def get_edges(self, book_id: int) -> List["StoryEdgeSchema"]:
        result = await self.session.execute(
            select(StoryEdge).where(StoryEdge.book_id == book_id).order_by(StoryEdge.id)
        )
        rows = result.scalars().all()
        from src.models.api_schemas import StoryEdgeSchema

        return [
            StoryEdgeSchema(
                id=f"edge-{row.id}",
                book_id=row.book_id,
                source=row.source,
                target=row.target,
                kind=row.kind,
                data=self._parse_data(row.data),
            )
            for row in rows
        ]

    async def get_canvas(self, book_id: int) -> "StoryCanvasResponse":
        nodes = await self.get_nodes(book_id)
        edges = await self.get_edges(book_id)
        from src.models.api_schemas import StoryCanvasResponse

        return StoryCanvasResponse(nodes=nodes, edges=edges)

    @retry_on_lock()
    async def upsert_node(
        self,
        book_id: int,
        kind: str,
        label: str,
        x: float,
        y: float,
        data: Optional[Dict[str, Any]] = None,
        ep_num: Optional[int] = None,
        character_id: Optional[int] = None,
        node_id: Optional[int] = None,
    ) -> StoryNode:
        """ノードを作成または更新する。node_id 指定時は更新、未指定時は新規作成。"""
        if node_id is not None:
            result = await self.session.execute(
                select(StoryNode).where(StoryNode.id == node_id)
            )
            node = result.scalar_one_or_none()
            if not node:
                raise ValueError(f"StoryNode with id {node_id} not found")
        else:
            node = StoryNode(book_id=book_id)
            self.session.add(node)

        node.kind = kind
        node.label = label
        node.x = x
        node.y = y
        node.data = json.dumps(data or {}, ensure_ascii=False)
        node.ep_num = ep_num
        node.character_id = character_id

        await self.session.flush()
        return node

    @retry_on_lock()
    async def delete_node(self, node_id: int) -> bool:
        """ノードを削除する。関連エッジも連鎖削除される（DB制約で CASCADE なしのため手動で削除推奨）"""
        # まず関連エッジを削除
        await self.session.execute(
            delete(StoryEdge).where(
                (StoryEdge.source == f"node-{node_id}") | (StoryEdge.target == f"node-{node_id}")
            )
        )
        # ノード削除
        result = await self.session.execute(
            delete(StoryNode).where(StoryNode.id == node_id)
        )
        return result.rowcount > 0

    @retry_on_lock()
    async def create_edge(
        self,
        book_id: int,
        source: str,
        target: str,
        kind: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> StoryEdge:
        edge = StoryEdge(
            book_id=book_id,
            source=source,
            target=target,
            kind=kind,
            data=json.dumps(data or {}, ensure_ascii=False),
        )
        self.session.add(edge)
        await self.session.flush()
        return edge

    @retry_on_lock()
    async def delete_edge(self, edge_id: int) -> bool:
        result = await self.session.execute(
            delete(StoryEdge).where(StoryEdge.id == edge_id)
        )
        return result.rowcount > 0

    async def get_node_by_id(self, node_id: int) -> Optional[StoryNode]:
        result = await self.session.execute(
            select(StoryNode).where(StoryNode.id == node_id)
        )
        return result.scalar_one_or_none()

    async def get_edge_by_id(self, edge_id: int) -> Optional[StoryEdge]:
        result = await self.session.execute(
            select(StoryEdge).where(StoryEdge.id == edge_id)
        )
        return result.scalar_one_or_none()