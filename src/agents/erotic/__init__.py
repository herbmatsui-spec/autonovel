"""
erotic package - 官能・シーン整合性チェックの分割モジュール群。

元 src/agents/erotic_integrity.py (2770行) を責務別に分割:
  - vocabulary: キーワード定数
  - curve:      EroticCurve / EroticPoint
  - evaluator:  EroticQualityScorer / EroticQualityReport
  - continuity: 連続性トラッカー群
  - filter:     SceneTypeDetector / EroticIntegrityChecker
"""

from src.agents.erotic.continuity import (
    CharacterStateSnapshot,
    ContinuityReport,
    ContinuityTracker,
    SceneContinuityTracker,
    SceneStateSnapshot,
)
from src.agents.erotic.curve import EroticCurve, EroticPoint
from src.agents.erotic.evaluator import EroticQualityReport, EroticQualityScorer
from src.agents.erotic.filter import EroticIntegrityChecker, SceneTypeDetector
from src.agents.erotic.vocabulary import (
    COMBAT_KEYWORDS,
    CONSENT_ALL_CHARACTERS_KEYWORDS,
    CONSENT_CONTINUATION_KEYWORDS,
    CONSENT_EXPLICIT_KEYWORDS,
    CONSENT_IMPLICIT_KEYWORDS,
    CONSENT_REFUSAL_KEYWORDS,
    CONVERSATION_KEYWORDS,
    EXPLICIT_CONSENT_KEYWORDS,
    EXPLORATION_KEYWORDS,
    FORESHADOW_KEYWORDS,
    IMPLICIT_CONSENT_KEYWORDS,
    ITEM_KEYWORDS,
    MONOLOGUE_KEYWORDS,
    MUTUAL_CONSENT_KEYWORDS,
    REFUSAL_KEYWORDS,
    REST_KEYWORDS,
    SCENE_TYPES,
    SIMPLE_MUTUAL_CONSENT_KEYWORDS,
    TIME_KEYWORDS,
    TRAVEL_KEYWORDS,
)

__all__ = [
    "SCENE_TYPES",
    "COMBAT_KEYWORDS",
    "CONVERSATION_KEYWORDS",
    "EXPLORATION_KEYWORDS",
    "TRAVEL_KEYWORDS",
    "REST_KEYWORDS",
    "MONOLOGUE_KEYWORDS",
    "FORESHADOW_KEYWORDS",
    "TIME_KEYWORDS",
    "ITEM_KEYWORDS",
    "EXPLICIT_CONSENT_KEYWORDS",
    "IMPLICIT_CONSENT_KEYWORDS",
    "REFUSAL_KEYWORDS",
    "MUTUAL_CONSENT_KEYWORDS",
    "SIMPLE_MUTUAL_CONSENT_KEYWORDS",
    "CONSENT_EXPLICIT_KEYWORDS",
    "CONSENT_IMPLICIT_KEYWORDS",
    "CONSENT_REFUSAL_KEYWORDS",
    "CONSENT_ALL_CHARACTERS_KEYWORDS",
    "CONSENT_CONTINUATION_KEYWORDS",
    "EroticCurve",
    "EroticPoint",
    "EroticQualityReport",
    "EroticQualityScorer",
    "SceneStateSnapshot",
    "SceneContinuityTracker",
    "CharacterStateSnapshot",
    "ContinuityReport",
    "ContinuityTracker",
    "EroticIntegrityChecker",
    "SceneTypeDetector",
]
