import logging
from typing import Any

from src.models.db import BookDbModel  # 型注釈用（DTO定義: src/models/db.py）

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class MarketingGenerationWorkflow(BaseWorkflow):
    """マーケティング情報生成ワークフロー"""

    async def execute(self, reporter: StatusReporter | None = None, **kwargs) -> dict[str, Any]:
        book_id = kwargs["book_id"]
        latest_ep = kwargs["latest_ep"]
        prompt_manager = kwargs.get("prompt_manager")

        # 旧実装の repo.books.get_by_id は存在しないため、facade 直下の get_book を使う。
        if not self.repo:
            raise RuntimeError("Repository is required for MarketingGenerationWorkflow")
        book: BookDbModel | None = await self.repo.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        if reporter:
            reporter.set_message("マーケティングパックを生成中...")
            reporter.add_log("マーケティングエージェントを起動しました")

        marketing_agent = self.marketing
        if prompt_manager is not None:
            try:
                marketing_agent.prompt_manager = prompt_manager
            except Exception as exc:
                logger.debug("Failed to set prompt_manager on marketing_agent: %s", exc)

        result = await marketing_agent.generate_pack(
            book_title=book.title,
            synopsis=getattr(book, "synopsis", "") or "",
            latest_ep=latest_ep,
        )
        return result
