"""AutoNovel ドメインモデル集約エクスポート."""

from __future__ import annotations

from src.models.audit import (
    AuditIssue,
    CausalityAuditResult,
    CausalityLink,
    CriticDirective,
    CriticFeedback,
    DogfeedingReport,
    EasyModeInferenceResult,
    ForeshadowingItem,
    GapAnalysisReport,
    GlobalLogicRepairResult,
    HegemonyAuditResult,
    HegemonyOracleResult,
    ImmersionScore,
    LogicalAuditIssueList,
    LogicalAuditResult,
    NarrativeWavePattern,
    ProducerPlanCandidate,
    StoredAuditIssue,
)
from src.models.base import (
    LLMRequestOptions,
    GenerateResult,
    FlatModelMixin,
)
from src.models.beat_sheet import (
    BeatSheetItem,
    BeatSheet,
    PlotVariantScore,
)
from src.models.bible import (
    StoryDNA,
    MarketingAssets,
    WorldBibleCore,
    WorldBible,
    NovelStructure,
    UltraFastWorldBible,
)
from src.models.character import (
    CharacterConcept,
    CharacterConceptList,
    CharacterRelationship,
    CharacterRegistry,
)
from src.infrastructure.database.models.chunk import ChapterChunk, Vector, HAS_PGVECTOR
from src.models.db import (
    BookDbModel,
    BibleDbModel,
    BranchDbModel,
    PlotDbModel,
    ChapterDbModel,
    CharacterDbModel,
)
from src.models.emotional_hook import (
    EmotionalHookSpec,
)
from src.models.entertainment_check import (
    EntertainmentCheckResult,
)
from src.models.illustration import (
    IllustrationType,
    IllustrationModel,
    SafetyLevel,
    IllustrationRequest,
    IllustrationResult,
)
from src.models.marketing import (
    TitleProposal,
    TitleProposalList,
)
from src.models.narrative_metrics import (
    NarrativeMetricScore,
    NarrativeSceneEvaluation,
)
from src.models.narrative_metrics_db import (
    NarrativeMetric,
    NarrativeMetricDefinition,
)
from src.models.planning_config import (
    PlanningConfig,
)
from src.models.plot import (
    ReviewLog,
    DynamicPacing,
    SceneBeat,
    SceneBeatList,
    CliffhangerDef,
    SceneBeatBlock,
    MasterSceneBlock,
    PlotBlueprintPhase1,
    PlotBlueprintPhase1Batch,
    PlotBlueprintPhase2,
    BaseEngine,
    PlotCoreInfo,
    PlotAnalytics,
    PlotForeshadowing,
    RedHerringItem,
    EnigmaAnalytics,
    ComfortAnalytics,
    CoreEngineMixin,
    EnigmaMixin,
    ComfortMixin,
    PlotEpisodeBase,
    PlotEpisode,
    MysteryEpisode,
    SliceOfLifeEpisode,
    DramaEpisode,
    RoadmapItem,
    RoadmapList,
    ArcBlueprint,
    ArcList,
    UltraFastPlotBatch,
    PlotDetail,
    CatharsisPattern,
)
from src.models.production_config import (
    NovelProject,
    EpisodeGenerateRequest,
    EpisodeResult,
    ProductionProgress,
)
from src.models.prompt_version import (
    PromptVersionDbModel,
)
from src.models.report import (
    TokenUsageReport,
    QualityMetricsReport,
    EpisodeSummary,
    ProductionReport,
)
from src.models.sharp_edge import (
    SharpEdgeSpec,
)
from src.models.task import (
    Task,
)
from src.models.world import (
    NarrativeConstraint,
    Foreshadowing,
    ClimaxScene,
    WorldRules,
    AnchorResponse,
    StoryThread,
    WorldState,
    RecoveredItem,
    ForeshadowingAudit,
)
from src.models.writing import (
    EpisodeDraft,
    CharacterStatusChange,
    EpisodeMetadata,
    EpisodeFinalDraft,
    StyleDNA,
    StyleFragment,
    MarketingPack,
    WritingContext,
    FullAutoWorkflowResult,
    PlanGenerationResult,
    PlotExpansionResult,
    RetryFailedEpisodesResult,
    EpisodeWritingResult,
    PlotRebuildResult,
)
from src.models.editor import (
    SensoryType,
    ToneType,
    AssistAction,
    AssistRequest,
    AssistResponse,
    GraphEvidenceNode,
    AskBibleRequest,
    AskBibleResponse,
    ConsistencyIssue,
    ConsistencyAuditRequest,
    ConsistencyAuditResponse,
    BranchType,
    BeatCard,
    NextBeatsRequest,
    NextBeatsResponse,
)
# 後方互換用遅延インポート (ORM循環インポート/起動ブロッキング回避)
def __getattr__(name: str):
    if name in ("Bible", "Book", "Chapter", "Character", "Plot"):
        import src.backend.database.models as _backend_models
        return getattr(_backend_models, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "ChapterChunk",
    "Vector",
    "HAS_PGVECTOR",
    "Bible",
    "Book",
    "Chapter",
    "Character",
    "Plot",
]
