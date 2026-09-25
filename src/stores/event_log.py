"""EventLog ストア実装 (Week 2 Step 12)。

感情シグナルを JSONL (append-only) に永続化し、クエリ・リプレイを提供する。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional, Tuple

from src.pipeline.emotional_residue import EmotionalSignal
from src.pipeline.emotional_residue import EmotionType
from src.rules.state_machine import EmotionalStateMachine

logger = logging.getLogger(__name__)

# デフォルトのログファイルパス (リポジトリルート相関)
DEFAULT_LOG_PATH = str(Path(__file__).resolve().parents[2] / "data" / "emotional_events.jsonl")


class EventLogStore:
    """JSONL append-only の感情イベントログストア。

    Args:
        path: ログファイルパス (1行1イベント JSON)
    """

    def __init__(self, path: str = DEFAULT_LOG_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 書き込み
    # ------------------------------------------------------------------
    def append(self, signal: EmotionalSignal) -> None:
        """シグナルを 1 行追加する。"""
        entry = {
            **asdict(signal),
            "emotion_type": signal.emotion_type.value if hasattr(signal.emotion_type, "value") else str(signal.emotion_type),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------
    # 読み取り
    # ------------------------------------------------------------------
    def _iter_entries(self) -> List[dict]:
        """全エントリをロードする (ファイル未存在時は空)。"""
        if not self.path.exists():
            return []
        entries: List[dict] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning("Skipping malformed JSONL line: %s", e)
        return entries

    @staticmethod
    def _entry_to_signal(entry: dict) -> EmotionalSignal:
        """エントリ辞書から EmotionalSignal を復元する。"""
        data = dict(entry)
        emo_raw = data.get("emotion_type", "affection")
        try:
            data["emotion_type"] = EmotionType(str(emo_raw))
        except ValueError:
            data["emotion_type"] = EmotionType.AFFECTION
        return EmotionalSignal(
            source=data.get("source", ""),
            target=data.get("target", ""),
            emotion_type=data["emotion_type"],
            value=float(data.get("value", 0.0)),
            confidence=float(data.get("confidence", 1.0)),
            evidence_span=data.get("evidence_span", ""),
            episode_id=data.get("episode_id", ""),
            cause=data.get("cause"),
            hidden=bool(data.get("hidden", False)),
        )

    def query(
        self,
        pair: Optional[Tuple[str, str]] = None,
        from_ep: int = 0,
        to_ep: int = 10**9,
    ) -> List[EmotionalSignal]:
        """条件に一致するシグナルをクエリする。

        Args:
            pair: (source, target) ペア指定 (None なら全件)
            from_ep: 開始エピソード番号 (含む)
            to_ep: 終了エピソード番号 (含む)

        Returns:
            一致した EmotionalSignal のリスト (追加順)
        """
        result: List[EmotionalSignal] = []
        for entry in self._iter_entries():
            if pair is not None:
                if entry.get("source") != pair[0] or entry.get("target") != pair[1]:
                    continue
            ep = self._extract_episode(entry.get("episode_id", ""))
            if ep is None:
                continue
            if from_ep <= ep <= to_ep:
                result.append(self._entry_to_signal(entry))
        return result

    def replay_to_episode(self, episode: int) -> EmotionalStateMachine:
        """ログを全再生して指定エピソードまでの状態を復元する。

        ログに記録された value は「適用後の状態値」のため、再生時は
        記録値を最終値として直接設定する。

        Args:
            episode: 復元先のエピソード番号 (含む)

        Returns:
            状態を復元した EmotionalStateMachine
        """
        sm = EmotionalStateMachine()
        for entry in self._iter_entries():
            ep = self._extract_episode(entry.get("episode_id", ""))
            if ep is None or ep > episode:
                continue
            emo_raw = entry.get("emotion_type", "affection")
            try:
                emo = EmotionType(str(emo_raw))
            except ValueError:
                continue
            sm.set_value(
                entry.get("source", ""),
                entry.get("target", ""),
                emo,
                float(entry.get("value", 0.0)),
            )
        return sm

    @staticmethod
    def _extract_episode(episode_id: str) -> Optional[int]:
        """"ep14" 形式の ID からエピソード番号を抽出。"""
        text = str(episode_id).strip().lower()
        if text.startswith("ep"):
            try:
                return int(text[2:])
            except ValueError:
                return None
        return None

    def count(self) -> int:
        """記録済みエントリ数。"""
        return len(self._iter_entries())

    def delete_by_beat_id(self, episode: int, beat_id: str) -> int:
        """指定 beat_id・エピソードのエントリを削除する（物理削除）。
        
        Args:
            episode: エピソード番号
            beat_id: ビートID
            
        Returns:
            削除された行数
        """
        if not self.path.exists():
            return 0
        
        deleted = 0
        kept_entries = []
        
        for entry in self._iter_entries():
            entry_ep = self._extract_episode(entry.get("episode_id", ""))
            entry_beat_id = entry.get("beat_id", "")
            
            if entry_ep == episode and entry_beat_id == beat_id:
                deleted += 1
            else:
                kept_entries.append(entry)
        
        # ファイルを書き直し
        with self.path.open("w", encoding="utf-8") as f:
            for entry in kept_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return deleted


__all__ = ["EventLogStore", "DEFAULT_LOG_PATH"]
