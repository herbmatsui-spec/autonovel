"""
kernels/dialogue.py - 対話機能
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class DialoguePhase(str, Enum):
    """対話の段階"""

    OPENING = "opening"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    EPILOGUE = "epilogue"


@dataclass
class DialogueTurn:
    """対話の1ターン"""

    turn_id: str
    speaker: str
    content: str
    phase: DialoguePhase = DialoguePhase.DEVELOPMENT
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueSession:
    """対話セッション"""

    session_id: str
    participant: str
    turns: List[DialogueTurn] = field(default_factory=list)
    current_phase: DialoguePhase = DialoguePhase.OPENING
    context: Dict[str, Any] = field(default_factory=dict)


class DialogueManager:
    """
    対話セッションの生成・進行・終結を管理するマネージャ。

    本実装は「対話進行カーネル」としての薄いオーケストレータで、
    セッションの作成・ターン追加・位相遷移・終了検出を提供する。
    """

    def __init__(self, max_turns: int = 50) -> None:
        self.max_turns = max_turns
        self._sessions: Dict[str, DialogueSession] = {}

    def create_session(
        self,
        session_id: str,
        participant: str,
        context: Dict[str, Any] | None = None,
    ) -> DialogueSession:
        session = DialogueSession(
            session_id=session_id,
            participant=participant,
            context=context or {},
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> DialogueSession | None:
        return self._sessions.get(session_id)

    def add_turn(
        self,
        session_id: str,
        speaker: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> DialogueTurn:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"DialogueSession not found: {session_id}")
        turn = DialogueTurn(
            turn_id=f"{session_id}-{len(session.turns) + 1}",
            speaker=speaker,
            content=content,
            phase=session.current_phase,
            metadata=metadata or {},
        )
        session.turns.append(turn)
        if len(session.turns) >= self.max_turns:
            session.current_phase = DialoguePhase.RESOLUTION
        return turn

    def advance_phase(self, session_id: str, next_phase: DialoguePhase) -> DialoguePhase:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"DialogueSession not found: {session_id}")
        session.current_phase = next_phase
        return next_phase

    def is_finished(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return True
        return session.current_phase in (DialoguePhase.RESOLUTION, DialoguePhase.EPILOGUE)

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
