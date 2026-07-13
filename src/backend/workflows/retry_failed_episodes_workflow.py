from typing import Any, Dict

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class RetryFailedEpisodesWorkflow(BaseWorkflow):
    """失敗したエピソードをスキャンし、自動で再試行・修復するバックグラウンドジョブ"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        passion = kwargs["passion"]
        word_count = kwargs["word_count"]

        book = await self.engine.repo.get_book(book_id)
        target_eps = book.target_eps if book else 50
        chars, failed = await self.engine.writer.generate_episodes_pipeline(
            book_id, 1, target_eps, passion, word_count, reporter=reporter, is_easy_mode=True
        )
        return {"chars_count": chars, "failed_episodes": failed, "book_id": book_id}
