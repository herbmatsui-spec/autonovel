import json
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import Outbox


class ChromaOutboxService:
    """
    ChromaDB同期用のアウトボックスイベントのデータベース永続化を担当するサービス。
    """
    async def flush(self, session: AsyncSession, additions: List[Dict[str, Any]], deletions: List[Dict[str, Any]]):
        """
        ステージングされた追加および削除のイベントを Outbox テーブルに追加する。
        """
        for add in additions:
            payload = json.dumps(add, ensure_ascii=False)
            event = Outbox(event_type="chroma_add", payload=payload)
            session.add(event)
        for delete in deletions:
            payload = json.dumps(delete, ensure_ascii=False)
            event = Outbox(event_type="chroma_delete", payload=payload)
            session.add(event)

