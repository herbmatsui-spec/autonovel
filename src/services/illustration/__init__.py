"""illustration サービスパッケージ。

統合イラスト生成エンジン（`UnifiedIllustrationGenerator`）を主入口とし、
旧来の個別サービス（`CoverGenerator` / `CharacterIllustrator` /
`SceneIllustrationService` / `YonkomaIllustrator`）は後方互換のため
併存させる。生成モデルは `config/image_models.py` のカタログで一元管理し、
既定は NanoBanana2Lite。
"""

from src.services.illustration.character_ref import CharacterReferenceManager
from src.services.illustration.character_service import CharacterIllustrator
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.cover_service import CoverGenerator
from src.services.illustration.quality_gate import QualityEvaluation, QualityGate
from src.services.illustration.scene_service import (
    SceneExtractor,
    SceneIllustrationService,
    SceneIllustrator,
    YonkomaIllustrator,
    YonkomaPlanner,
)
from src.services.illustration.typesetter import Typesetter
from src.services.illustration.unified_generator import UnifiedIllustrationGenerator
from src.services.illustration.upscaler import Upscaler

__all__ = [
    "CharacterIllustrator",
    "CharacterReferenceManager",
    "CoverGenerator",
    "QualityEvaluation",
    "QualityGate",
    "SceneExtractor",
    "SceneIllustrator",
    "SceneIllustrationService",
    "Typesetter",
    "UnifiedIllustrationConfig",
    "UnifiedIllustrationGenerator",
    "Upscaler",
    "YonkomaIllustrator",
    "YonkomaPlanner",
]
