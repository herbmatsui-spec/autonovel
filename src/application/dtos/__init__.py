"""Application DTOs package."""

from src.application.dtos.common import (
    PaginationDTO,
    PaginatedResponseDTO,
    ErrorResponseDTO,
    SuccessResponseDTO,
    ValidationErrorDTO,
)
from src.application.dtos.novel_dto import (
    CreateNovelDTO,
    UpdateNovelDTO,
    NovelResponseDTO,
    NovelListItemDTO,
    NovelSearchDTO,
)
from src.application.dtos.chapter_dto import (
    CreateChapterDTO,
    UpdateChapterDTO,
    ChapterResponseDTO,
    ChapterListItemDTO,
    ReorderChaptersDTO,
)
from src.application.dtos.episode_dto import (
    WriteEpisodeDTO,
    RewriteEpisodeDTO,
    EpisodeResponseDTO,
    EpisodeDraftDTO,
    EpisodeListItemDTO,
    ExpandPlotDTO,
)
from src.application.dtos.plot_dto import (
    GeneratePlotDTO,
    PlotExpansionDTO,
    CreatePlotPointDTO,
    UpdatePlotPointDTO,
    CreateArcDTO,
    PlotPointResponseDTO,
    ArcResponseDTO,
    PlotResponseDTO,
    PlotListItemDTO,
)
from src.application.dtos.bible_dto import (
    GenerateBibleDTO,
    CreateSettingDTO,
    UpdateSettingDTO,
    CreateLoreDTO,
    UpdateLoreDTO,
    SettingDTO,
    LoreDTO,
    BibleResponseDTO,
    BibleListItemDTO,
)
from src.application.dtos.audit_dto import (
    AuditRequestDTO,
    AuditFindingDTO,
    AuditResponseDTO,
    AuditListItemDTO,
    AuditHistoryFilterDTO,
)
from src.application.dtos.branch_dto import (
    CreateBranchDTO,
    UpdateBranchDTO,
    BranchResponseDTO,
    BranchListItemDTO,
    CreateBranchPlaySessionDTO,
    BranchPlaySessionResponseDTO,
)
from src.application.dtos.illustration_dto import (
    GenerateCharacterIllustrationDTO,
    GenerateCoverIllustrationDTO,
    GenerateSceneIllustrationDTO,
    IllustrationResponseDTO,
)

__all__ = [
    # Common
    "PaginationDTO",
    "PaginatedResponseDTO",
    "ErrorResponseDTO",
    "SuccessResponseDTO",
    "ValidationErrorDTO",
    # Novel
    "CreateNovelDTO",
    "UpdateNovelDTO",
    "NovelResponseDTO",
    "NovelListItemDTO",
    "NovelSearchDTO",
    # Chapter
    "CreateChapterDTO",
    "UpdateChapterDTO",
    "ChapterResponseDTO",
    "ChapterListItemDTO",
    "ReorderChaptersDTO",
    # Episode
    "WriteEpisodeDTO",
    "RewriteEpisodeDTO",
    "EpisodeResponseDTO",
    "EpisodeDraftDTO",
    "EpisodeListItemDTO",
    "ExpandPlotDTO",
    # Plot
    "GeneratePlotDTO",
    "PlotExpansionDTO",
    "CreatePlotPointDTO",
    "UpdatePlotPointDTO",
    "CreateArcDTO",
    "PlotPointResponseDTO",
    "ArcResponseDTO",
    "PlotResponseDTO",
    "PlotListItemDTO",
    # Bible
    "GenerateBibleDTO",
    "CreateSettingDTO",
    "UpdateSettingDTO",
    "CreateLoreDTO",
    "UpdateLoreDTO",
    "SettingDTO",
    "LoreDTO",
    "BibleResponseDTO",
    "BibleListItemDTO",
    # Audit
    "AuditRequestDTO",
    "AuditFindingDTO",
    "AuditResponseDTO",
    "AuditListItemDTO",
    "AuditHistoryFilterDTO",
    # Branch
    "CreateBranchDTO",
    "UpdateBranchDTO",
    "BranchResponseDTO",
    "BranchListItemDTO",
    "CreateBranchPlaySessionDTO",
    "BranchPlaySessionResponseDTO",
    # Illustration
    "GenerateCharacterIllustrationDTO",
    "GenerateCoverIllustrationDTO",
    "GenerateSceneIllustrationDTO",
    "IllustrationResponseDTO",
]
