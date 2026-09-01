import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import Outbox


class ChromaOutboxService:
    """
    ChromaDB同期用のアウトボックスイベントのデータベース永続化を担当するサービス。
    """

    async def flush(
        self,
        session: AsyncSession,
        additions: list[dict[str, Any]],
        deletions: list[dict[str, Any]],
    ):
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
