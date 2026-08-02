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
