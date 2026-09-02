from typing import Any

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class MarketingGenerationWorkflow(BaseWorkflow):
    """マーケティング情報生成ワークフロー"""

    async def execute(self, reporter: StatusReporter | None = None, **kwargs) -> dict[str, Any]:
        book_id = kwargs["book_id"]
        latest_ep = kwargs["latest_ep"]
        prompt_manager = kwargs.get("prompt_manager")

        book = await self.repo.books.get_by_id(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        if reporter:
            reporter.set_message("マーケティングパックを生成中...")
            reporter.add_log("マーケティングエージェントを起動しました")

        marketing_agent = self.marketing
        if prompt_manager is not None:
            try:
                marketing_agent.prompt_manager = prompt_manager
            except Exception:
                pass

        result = await marketing_agent.generate_pack(
            book_title=book.title,
            synopsis=getattr(book, "synopsis", "") or "",
            latest_ep=latest_ep,
        )
        return result
