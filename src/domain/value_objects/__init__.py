"""Domain value objects package."""

from src.domain.value_objects.ids import (
    NovelId,
    ChapterId,
    EpisodeId,
    CharacterId,
    BranchId,
    PlotId,
    SettingId,
    AuditId,
    UserId,
)

from src.domain.value_objects.text import (
    TextFormat,
    TextContent,
    PlainText,
    MarkdownText,
    HtmlText,
    Title,
    Summary,
    Catchcopy,
    Genre,
)

from src.domain.value_objects.scores import (
    QualityScore,
    TensionScore,
    BookScore,
    QolScore,
    CostScore,
)

from src.domain.value_objects.metadata import (
    NovelStatus,
    NovelMode,
    NovelMetadata,
    PublishPlatform,
    PublishStatus,
    PublishMetadata,
    ChapterMetadata,
    CharacterMetadata,
    BranchMetadata,
    AuditMetadata,
)

__all__ = [
    # IDs
    "NovelId",
    "ChapterId",
    "EpisodeId",
    "CharacterId",
    "BranchId",
    "PlotId",
    "SettingId",
    "AuditId",
    "UserId",
    # Text
    "TextFormat",
    "TextContent",
    "PlainText",
    "MarkdownText",
    "HtmlText",
    "Title",
    "Summary",
    "Catchcopy",
    "Genre",
    # Scores
    "QualityScore",
    "TensionScore",
    "BookScore",
    "QolScore",
    "CostScore",
    # Metadata
    "NovelStatus",
    "NovelMode",
    "NovelMetadata",
    "PublishPlatform",
    "PublishStatus",
    "PublishMetadata",
    "ChapterMetadata",
    "CharacterMetadata",
    "BranchMetadata",
    "AuditMetadata",
]