"""Domain services package."""

from src.domain.domain_services.plot_domain_service import (
    PlotDomainService,
    PlotValidationError,
    PlotStructureValidator,
    PlotIntegrityChecker,
    ChainPhase,
)

from src.domain.domain_services.character_domain_service import (
    CharacterDomainService,
    CharacterValidationError,
    CharacterValidator,
    CharacterConsistencyChecker,
    CharacterRelationshipManager,
    RelationshipType,
    CharacterRelationship,
    CharacterConsistencyIssue,
)

from src.domain.domain_services.bible_domain_service import (
    BibleDomainService,
    BibleValidationError,
    BibleValidator,
    BibleConsistencyChecker,
    SettingConflict,
    SettingConflictType,
    ConsistencyReport,
)

from src.domain.domain_services.quality_domain_service import (
    QualityDomainService,
    QualityValidator,
    QualityCalculator,
    QualityAnalyzer,
    QualityValidationError,
    QualityGrade,
    QualityThresholds,
)

__all__ = [
    # Plot
    "PlotDomainService",
    "PlotValidationError",
    "PlotStructureValidator",
    "PlotIntegrityChecker",
    "ChainPhase",
    # Character
    "CharacterDomainService",
    "CharacterValidationError",
    "CharacterValidator",
    "CharacterConsistencyChecker",
    "CharacterRelationshipManager",
    "RelationshipType",
    "CharacterRelationship",
    "CharacterConsistencyIssue",
    # Bible
    "BibleDomainService",
    "BibleValidationError",
    "BibleValidator",
    "BibleConsistencyChecker",
    "SettingConflict",
    "SettingConflictType",
    "ConsistencyReport",
    # Quality
    "QualityDomainService",
    "QualityValidator",
    "QualityCalculator",
    "QualityAnalyzer",
    "QualityValidationError",
    "QualityGrade",
    "QualityThresholds",
]
