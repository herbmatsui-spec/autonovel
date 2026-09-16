"""Application use cases package."""

from src.application.use_cases.audit_use_cases import (
    RequestAuditUseCase,
    GetAuditUseCase,
    ListAuditsUseCase,
    AddAuditFindingUseCase,
    RemoveAuditFindingUseCase,
    CompleteAuditUseCase,
)
from src.application.use_cases.branch_use_cases import (
    CreateBranchUseCase,
    GetBranchUseCase,
    ListBranchesUseCase,
    UpdateBranchUseCase,
    DeleteBranchUseCase,
    CreateBranchPlaySessionUseCase,
)
from src.application.use_cases.illustration_use_cases import (
    GenerateCharacterIllustrationUseCase,
    GenerateCoverIllustrationUseCase,
    GenerateSceneIllustrationUseCase,
)
from src.application.use_cases.novel_use_cases import (
    CreateNovelUseCase,
    GetNovelUseCase,
    ListNovelsUseCase,
    UpdateNovelUseCase,
    DeleteNovelUseCase,
    ChangeNovelStatusUseCase,
    SetNovelModeUseCase,
    AddNovelCostUseCase,
    GetLatestNovelsUseCase,
)
from src.application.use_cases.chapter_use_cases import (
    CreateChapterUseCase,
    GetChapterUseCase,
    ListChaptersUseCase,
    UpdateChapterUseCase,
    DeleteChapterUseCase,
    ReorderChaptersUseCase,
)
from src.application.use_cases.writing_use_cases import (
    WriteEpisodeUseCase,
    RewriteEpisodeUseCase,
    GetEpisodeUseCase,
    ListEpisodesUseCase,
    DeleteEpisodeUseCase,
    ExpandPlotIntoEpisodeUseCase,
)
from src.application.use_cases.book_use_cases import BookUseCases


__all__ = [
    # Audit
    "RequestAuditUseCase",
    "GetAuditUseCase",
    "ListAuditsUseCase",
    "AddAuditFindingUseCase",
    "RemoveAuditFindingUseCase",
    "CompleteAuditUseCase",
    # Branch
    "CreateBranchUseCase",
    "GetBranchUseCase",
    "ListBranchesUseCase",
    "UpdateBranchUseCase",
    "DeleteBranchUseCase",
    "CreateBranchPlaySessionUseCase",
    # Illustration
    "GenerateCharacterIllustrationUseCase",
    "GenerateCoverIllustrationUseCase",
    "GenerateSceneIllustrationUseCase",
    # Novel
    "CreateNovelUseCase",
    "GetNovelUseCase",
    "ListNovelsUseCase",
    "UpdateNovelUseCase",
    "DeleteNovelUseCase",
    "ChangeNovelStatusUseCase",
    "SetNovelModeUseCase",
    "AddNovelCostUseCase",
    "GetLatestNovelsUseCase",
    # Chapter
    "CreateChapterUseCase",
    "GetChapterUseCase",
    "ListChaptersUseCase",
    "UpdateChapterUseCase",
    "DeleteChapterUseCase",
    "ReorderChaptersUseCase",
    # Writing
    "WriteEpisodeUseCase",
    "RewriteEpisodeUseCase",
    "GetEpisodeUseCase",
    "ListEpisodesUseCase",
    "DeleteEpisodeUseCase",
    "ExpandPlotIntoEpisodeUseCase",
]
