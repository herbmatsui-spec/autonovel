from typing import Any, Dict, Optional

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class ChapterImportWorkflow(BaseWorkflow):
    """本文インポートワークフロー"""
    async def execute(self, reporter: Optional[StatusReporter] = None, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        ep_num = kwargs["ep_num"]
        import_text = kwargs["import_text"]
        do_refine = kwargs["do_refine"]

        result = await self.engine.writer.analyze_and_import_chapter(
            book_id, ep_num, import_text, do_refine=do_refine
        )
        return result
