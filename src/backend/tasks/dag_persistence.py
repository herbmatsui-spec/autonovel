"""DAG Checkpoint/Resume Persistence (Step 6)."""
from __future__ import annotations

from typing import Protocol, Optional
from src.backend.tasks.dag_models import DAGGraph


class DAGPersistence(Protocol):
    """DAG 状態の永続化プロトコル。"""
    def save_checkpoint(self, graph: DAGGraph, checkpoint_id: str) -> None:
        """グラフ状態をチェックポイント保存。"""
        ...
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[DAGGraph]:
        """チェックポイントからグラフ復元。"""
        ...
    
    def list_checkpoints(self, dag_id: str) -> list[str]:
        """指定 DAG のチェックポイント一覧。"""
        ...
    
    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """チェックポイント削除。"""
        ...


import json
from pathlib import Path
from datetime import datetime


class FileSystemDAGPersistence:
    """ローカルファイルシステムへの JSON 保存。"""
    def __init__(self, base_dir: str = "/tmp/dag_checkpoints"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        return self.base_dir / f"{checkpoint_id}.json"
    
    def save_checkpoint(self, graph: DAGGraph, checkpoint_id: str) -> None:
        # Pydantic モデルを JSON シリアライズ
        data = graph.model_dump(mode="json")
        data["_checkpoint_meta"] = {
            "saved_at": datetime.now().isoformat(),
            "dag_id": graph.dag_id,
            "checkpoint_id": checkpoint_id
        }
        path = self._checkpoint_path(checkpoint_id)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[DAGGraph]:
        path = self._checkpoint_path(checkpoint_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        meta = data.pop("_checkpoint_meta", {})
        return DAGGraph.model_validate(data)
    
    def list_checkpoints(self, dag_id: str) -> list[str]:
        checkpoints = []
        for path in self.base_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("_checkpoint_meta", {}).get("dag_id") == dag_id:
                    checkpoints.append(path.stem)
            except Exception:
                pass
        return sorted(checkpoints)
    
    def delete_checkpoint(self, checkpoint_id: str) -> None:
        self._checkpoint_path(checkpoint_id).unlink(missing_ok=True)


# Redis 実装 (オプション)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore


class RedisDAGPersistence:
    """Redis への JSON 保存 (分散環境用)。"""
    def __init__(self, url: str = "redis://localhost:6379", ttl: int = 86400):
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis not installed. Install with: pip install redis")
        self.client = redis.from_url(url, decode_responses=True)
        self.ttl = ttl
    
    def _key(self, checkpoint_id: str) -> str:
        return f"dag:checkpoint:{checkpoint_id}"
    
    def save_checkpoint(self, graph: DAGGraph, checkpoint_id: str) -> None:
        data = graph.model_dump_json()
        self.client.setex(self._key(checkpoint_id), self.ttl, data)
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[DAGGraph]:
        data = self.client.get(self._key(checkpoint_id))
        if not data:
            return None
        return DAGGraph.model_validate_json(data)
    
    def list_checkpoints(self, dag_id: str) -> list[str]:
        pattern = "dag:checkpoint:*"
        checkpoints = []
        for key in self.client.scan_iter(match=pattern):
            data = self.client.get(key)
            if data:
                import json
                meta = json.loads(data).get("_checkpoint_meta", {})
                if meta.get("dag_id") == dag_id:
                    checkpoints.append(key.split(":")[-1])
        return sorted(checkpoints)
    
    def delete_checkpoint(self, checkpoint_id: str) -> None:
        self.client.delete(self._key(checkpoint_id))


__all__ = [
    "DAGPersistence",
    "FileSystemDAGPersistence",
    "RedisDAGPersistence",
    "REDIS_AVAILABLE",
]