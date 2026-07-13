from typing import Any, Dict, Optional

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class MarketingGenerationWorkflow(BaseWorkflow):
    """マーケティング情報生成ワークフロー"""
    async def execute(self, reporter: Optional[StatusReporter] = None, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        latest_ep = kwargs["latest_ep"]

        book = await self.engine.repo.books.get_by_id(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        if reporter:
            reporter.set_message("マーケティングパックを生成中...")
            reporter.add_log("マーケティングエージェントを起動しました")

        result = await self.engine.marketing.generate_marketing_pack(
            book.title, book.synopsis, latest_ep
        )
        return result
