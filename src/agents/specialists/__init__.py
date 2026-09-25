"""Phase 2: 8 Specialist Auditors package (v5.0 Unified Architecture).

Note on v5.0 Refactoring:
8並列オーディター（Consistency, Emotion, Style等）は、アテンション希釈とコスト爆発を防止するため、
二層ハイブリッド監査エンジン `UnifiedAuditor`（静的ルール解析0ms + 単一LLM定性判定）へ集約されました。
既存コードとの後方互換性のため旧クラスもエクスポートされていますが、新規開発では `UnifiedAuditor` を使用してください。
"""

from src.agents.specialists.unified_auditor import UnifiedAuditor
from src.agents.specialists.anti_ai_detector import AntiAIDetector
from src.agents.specialists.consistency_auditor import ConsistencyAuditor
from src.agents.specialists.creativity_auditor import CreativityAuditor
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.agents.specialists.emotion_curve_auditor import EmotionCurveAuditor
from src.agents.specialists.style_auditor import StyleAuditor
from src.agents.specialists.factual_auditor import FactualAuditor
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialists.multimodal_auditor import MultimodalAuditor
from src.agents.specialists.adapter import AuditAggregatorNode

__all__ = [
    "UnifiedAuditor",
    "AntiAIDetector",
    "ConsistencyAuditor",
    "CreativityAuditor",
    "ReaderHookAuditor",
    "EmotionCurveAuditor",
    "StyleAuditor",
    "FactualAuditor",
    "StructureAuditor",
    "MultimodalAuditor",
    "AuditAggregatorNode",
]