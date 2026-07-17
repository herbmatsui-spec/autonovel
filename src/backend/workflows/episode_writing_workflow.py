import logging
from typing import Any, Dict

from src.shared.utils import StatusReporter

from ._shared_ops import enqueue_shadow_audit, trigger_prefetch
from .base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)

class EpisodeWritingWorkflow(BaseWorkflow):
    """執筆ワークフロー: 通常モードとパイプラインモードの切り替えを隠蔽"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        write_from = kwargs["write_from"]
        write_to = kwargs["write_to"]
        passion = kwargs["passion"]
        word_count = kwargs["word_count"]
        do_refine = kwargs["do_refine"]
        env_state = kwargs["env_state"]
        pipeline_mode = kwargs["pipeline_mode"]
        mode = kwargs.get("mode", "final")

        if pipeline_mode:
            chars_count, failed = await self.engine.writer.generate_episodes_pipeline(
                book_id, write_from, write_to, passion, word_count, reporter=reporter,
                mode=mode
            )
            # 執筆完了後にプリフェッチを実行して次のエピソード生成を高速化
            await trigger_prefetch(self.engine, book_id, write_to, reporter)
            # 非同期で監査を走らせる (Shadow Mode)
            await enqueue_shadow_audit(book_id, write_from, write_to, reporter)
            return {"chars_count": chars_count, "failed_episodes": failed, "book_id": book_id}
        else:
            chars_count = await self.engine.writer.generate_episodes(
                book_id, write_from, write_to, passion, word_count, do_refine,
                reporter=reporter, env_state=env_state, mode=mode
            )
            # 執筆完了後にプリフェッチを実行して次のエピソード生成を高速化
            await trigger_prefetch(self.engine, book_id, write_to, reporter)
            # 非同期で監査を走らせる (Shadow Mode)
            await enqueue_shadow_audit(book_id, write_from, write_to, reporter)
            return {"chars_count": chars_count, "book_id": book_id}

