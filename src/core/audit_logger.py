from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    timestamp: str
    user_id: str
    action: str
    resource_id: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: str = "unknown"


logger = logging.getLogger(__name__)

class AuditLogger:
    """
    システムの全操作を記録する監査ログマネージャー。
    ファイルベースの永続化を行い、後からの追跡を可能にする。
    """
    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"

    def log(self, user_id: str, action: str, resource_id: str, status: str, details: Optional[Dict[str, Any]] = None, ip_address: str = "unknown"):
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            action=action,
            resource_id=resource_id,
            status=status,
            details=details or {},
            ip_address=ip_address
        )

        log_line = f"[{entry.timestamp}] USER:{entry.user_id} ACTION:{entry.action} RES:{entry.resource_id} STATUS:{entry.status} IP:{entry.ip_address} DETAILS:{entry.details}\n"

        try:
            with open(self._current_log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")

    def get_logs_for_resource(self, resource_id: str) -> List[str]:
        """特定リソースに関する操作履歴を抽出する"""
        results = []
        # 簡易的に全ログファイルから検索
        for log_file in self.log_dir.glob("*.log"):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if f"RES:{resource_id}" in line:
                        results.append(line.strip())
        return results
