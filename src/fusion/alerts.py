"""Conflict alerting system across log, file and webhook channels."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from src.fusion.config import FusionConfig, load_fusion_config
from src.fusion.models import Conflict

logger = logging.getLogger("fusion.alerts")


class ConflictAlerter:
    """感情の矛盾が検出された際に警告・通知を発行するクラス"""

    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or load_fusion_config()

    def format_alert_payload(
        self,
        conflicts: List[Conflict],
        episode: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """アラートペイロードを作成"""
        items = []
        for c in conflicts:
            rec_action = "Review author intention in annotation vs plot rule / pipeline extraction."
            items.append({
                "conflict_id": c.conflict_id,
                "pair": list(c.pair),
                "emotion": c.emotion.value if hasattr(c.emotion, "value") else str(c.emotion),
                "sources": [
                    {"namespace": s[0], "value": s[1], "confidence": s[2]}
                    for s in c.sources
                ],
                "recommended_action": rec_action,
            })

        return {
            "alert_type": "EMOTIONAL_CONFLICT_DETECTED",
            "episode": episode,
            "conflict_count": len(conflicts),
            "conflicts": items,
            "context": context or {},
        }

    def alert(
        self,
        conflicts: List[Conflict],
        episode: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """設定されたチャネルへアラートを送出する"""
        if not conflicts:
            return {"status": "no_conflicts"}

        payload = self.format_alert_payload(conflicts, episode, context)
        channels = self.config.alert_channels

        # 1. ログ出力
        if "log" in channels:
            logger.warning(
                f"[ConflictAlert] Episode {episode} detected {len(conflicts)} emotional conflicts: "
                f"{json.dumps(payload, ensure_ascii=False)}"
            )

        # 2. ファイル追記 (logs/conflicts_ep{episode}.jsonl)
        if "file" in channels or "log" in channels:
            log_dir = Path("logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"conflicts_ep{episode}.jsonl"
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"Failed to write conflict alert file {log_file}: {e}")

        # 3. Webhook 送信
        if "webhook" in channels and self.config.webhook_url:
            self._send_webhook(self.config.webhook_url, payload)

        return {"status": "alerted", "channels": channels, "payload": payload}

    def _send_webhook(self, url: str, payload: Dict[str, Any]) -> None:
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.info(f"Webhook delivered with status {resp.status}")
        except Exception as e:
            logger.warning(f"Failed to deliver conflict webhook to {url}: {e}")
