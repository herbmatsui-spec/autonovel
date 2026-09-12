"""Domain entities package."""

from src.domain.entities.novel import (
    Novel,
    Chapter,
    Episode,
    Volume,
)
from src.domain.entities.character import (
    Character,
    CharacterArc,
)
from src.domain.entities.world_bible import (
    WorldBible,
    PendingSetting,
    Setting,
    Lore,
)
from src.domain.entities.plot import (
    Plot,
    PlotPoint,
    Arc,
    PlotStatus,
    ChainPhase,
)
from src.domain.entities.branch import (
    Branch,
    BranchPlaySession,
    BranchPlayStatus,
)
from src.domain.entities.audit import (
    AuditFinding,
    AuditResult,
    AuditCategory,
    AuditSeverity,
    AuditStatus,
    AuditType,
)
from src.domain.entities.easy_mode import (
    CharacterParams,
    DigestRequest,
    DigestResponse,
    DigestStatus,
    EasyModeInput,
    GachaPlan,
    GachaPlanType,
    GachaRequest,
    GachaResponse,
    GenerationResponse,
    PromotionRequest,
    PromotionResponse,
)
from src.domain.entities.review_session import ReviewRound, ReviewSession

__all__ = [
    # Novel
    "Novel",
    "Chapter",
    "Episode",
    "Volume",
    # Character
    "Character",
    "CharacterArc",
    # World Bible
    "WorldBible",
    "PendingSetting",
    "Setting",
    "Lore",
    # Plot
    "Plot",
    "PlotPoint",
    "Arc",
    "PlotStatus",
    "ChainPhase",
    # Branch
    "Branch",
    "BranchPlaySession",
    "BranchPlayStatus",
    # Audit
    "AuditFinding",
    "AuditResult",
    "AuditCategory",
    "AuditSeverity",
    "AuditStatus",
    "AuditType",
    # Easy Mode
    "CharacterParams",
    "DigestRequest",
    "DigestResponse",
    "DigestStatus",
    "EasyModeInput",
    "GachaPlan",
    "GachaPlanType",
    "GachaRequest",
    "GachaResponse",
    "GenerationResponse",
    "PromotionRequest",
    "PromotionResponse",
    # Review Session
    "ReviewRound",
    "ReviewSession",
]