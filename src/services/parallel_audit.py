import asyncio
import logging
from typing import Any, List, Tuple

from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)

class ParallelAudit:
    """複数の監査を並列実行するユーティリティ"""
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service

    async def run(self, tasks: List[Tuple[str, Any]]) -> List[Any]:
        coros = []
        for task_name, payload in tasks:
            if task_name == "fast_plot":
                coros.append(self.audit_service.screen_plot(payload))
            elif task_name == "ability":
                coros.append(self.audit_service.audit_ability(*payload))
            elif task_name == "deai":
                coros.append(self.audit_service.audit_deai(payload))
            else:
                logger.warning(f"Unknown audit task: {task_name}")
                coros.append(asyncio.sleep(0, result=(True, "skipped")))
        return await asyncio.gather(*coros, return_exceptions=False)
