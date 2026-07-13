import json
import os
from datetime import datetime


class TraceLogger:
    def __init__(self, log_dir="logs/traces"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log_event(self, book_id: int, event_type: str, data: dict):
        log_file = os.path.join(self.log_dir, f"book_{book_id}.jsonl")
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

