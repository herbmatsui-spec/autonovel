"""CoreMemory implementation for in-memory resident agent memory with token budget and disk persistence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.memory.interfaces import BaseCoreMemory
from src.fusion.models import FusedVector


class CoreMemory(BaseCoreMemory):
    """執筆エージェントのコンテキストに常駐するコアメモリ"""

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = {
            "character_emotions": {},
            "relationship_dynamics": {},
            "active_hooks": [],
            "writing_style_notes": "",
        }
        if initial_data:
            self._data.update(initial_data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def dump(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._data))

    @property
    def character_emotions(self) -> Dict[str, Any]:
        return self._data.setdefault("character_emotions", {})

    @property
    def relationship_dynamics(self) -> Dict[str, Any]:
        return self._data.setdefault("relationship_dynamics", {})

    @property
    def active_hooks(self) -> List[str]:
        return self._data.setdefault("active_hooks", [])

    @property
    def writing_style_notes(self) -> str:
        return self._data.get("writing_style_notes", "")

    @writing_style_notes.setter
    def writing_style_notes(self, value: str) -> None:
        self._data["writing_style_notes"] = value

    def update_emotion(
        self,
        source: str,
        target: str,
        emotion: str,
        delta: float,
        reason: str = "",
        episode_label: str = "",
    ) -> float:
        """指定ペアの感情値をデルタ加算で更新する"""
        pair_key = f"{source}->{target}"
        emotions = self.character_emotions.setdefault(pair_key, {})
        current = emotions.get(emotion, 0.0)
        new_val = max(-1.0, min(1.0, current + delta))
        emotions[emotion] = round(new_val, 4)
        if reason:
            emotions["cause"] = reason
        if episode_label:
            emotions["updated"] = episode_label
        return new_val

    def load_fused_vector(self, fused: FusedVector, episode_label: str = "") -> None:
        """Week 4 の FusedVector を CoreMemory にミラーロードする"""
        for (src, tgt, emo), fval in fused.values.items():
            pair_key = f"{src}->{tgt}"
            emo_dict = self.character_emotions.setdefault(pair_key, {})
            emo_str = emo.value if hasattr(emo, "value") else str(emo)
            emo_dict[emo_str] = round(fval.value, 4)
            emo_dict["primary_source"] = fval.primary_source
            emo_dict["confidence"] = fval.confidence
            if episode_label:
                emo_dict["updated"] = episode_label

    def estimate_tokens(self) -> int:
        """JSON文字列長から概算トークン数を算出（日本語・JSON混在で約1.5文字〜2文字1トークン換算）"""
        dumped = json.dumps(self._data, ensure_ascii=False)
        return max(1, len(dumped) // 2)

    def compact_if_needed(self, max_tokens: int = 2000) -> bool:
        """トークン予算を超過している場合に古い感情履歴や解決済みフックを圧縮する"""
        if self.estimate_tokens() <= max_tokens:
            return False

        # 1. relationship_dynamics 内の trust_trajectory を直近10件に切り詰め
        for pair_key, dyn in self.relationship_dynamics.items():
            if isinstance(dyn, dict) and "trust_trajectory" in dyn:
                traj = dyn["trust_trajectory"]
                if len(traj) > 10:
                    dyn["trust_trajectory"] = traj[-10:]

        # 2. active_hooks の重複排除
        self._data["active_hooks"] = list(dict.fromkeys(self.active_hooks))

        return True

    def save_to_disk(self, file_path: str | Path) -> Path:
        """CoreMemory 内容を JSON ファイルに保存"""
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        return p

    def load_from_disk(self, file_path: str | Path) -> bool:
        """JSON ファイルから CoreMemory 内容を復元"""
        p = Path(file_path)
        if not p.exists():
            return False
        with open(p, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        return True


__all__ = ["CoreMemory"]
