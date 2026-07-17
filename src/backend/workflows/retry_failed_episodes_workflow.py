from typing import Any, Dict

from src.shared.utils import StatusReporter

from ._shared_ops import run_pipeline_with_retry
from .base_workflow import BaseWorkflow


class RetryFailedEpisodesWorkflow(BaseWorkflow):
    """失敗したエピソードをスキャンし、自動で再試行・修復するバックグラウンドジョブ"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        passion = kwargs["passion"]
        word_count = kwargs["word_count"]

        book = await self.engine.repo.get_book(book_id)
        target_eps = book.target_eps if book else 50
        chars, failed = await run_pipeline_with_retry(
            writer=self.engine.writer,
            book_id=book_id,
            start_ep=1,
            end_ep=target_eps,
            passion=passion,
            word_count=word_count,
            reporter=reporter,
            is_easy_mode=True,
            max_retries=0
        )
        return {"chars_count": chars, "failed_episodes": failed, "book_id": book_id}
