"""Bible domain service - pure business logic for world bible consistency and conflict detection."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from enum import Enum
import json

from src.domain.entities.world_bible import WorldBible, Setting, Lore, PendingSetting
from src.domain.value_objects.ids import NovelId, SettingId
from src.domain.value_objects.text import TextContent
from src.domain.repositories.world_bible_repository import IWorldBibleRepository


class BibleValidationError(Exception):
    """Raised when bible validation fails."""
    pass


class SettingConflictType(Enum):
    """Types of setting conflicts."""
    DIRECT_CONTRADICTION = "direct_contradiction"
    SEMANTIC_CONFLICT = "semantic_conflict"
    MISSING_DEPENDENCY = "missing_dependency"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    INCONSISTENT_VALUE = "inconsistent_value"


@dataclass
class SettingConflict:
    """Represents a conflict between settings."""
    conflict_type: SettingConflictType
    field_path: str
    existing_value: Any
    new_value: Any
    description: str
    severity: str = "warning"  # warning, error, critical
    related_settings: List[str] = field(default_factory=list)


@dataclass
class ConsistencyReport:
    """Report of world bible consistency check."""
    is_consistent: bool
    conflicts: List[SettingConflict]
    warnings: List[str]
    suggestions: List[str]
    checked_settings: int
    checked_lore: int


class BibleConsistencyChecker:
    """Checks world bible consistency and detects conflicts."""

    # Known setting dependencies (field -> required fields)
    SETTING_DEPENDENCIES = {
        "magic_system.mana_cost": ["magic_system.mana_source"],
        "magic_system.spell_slots": ["magic_system.mana_cost"],
        "technology.level": ["technology.era"],
        "geography.climate": ["geography.terrain"],
        "society.currency": ["society.economy_type"],
        "history.timeline": ["history.eras"],
    }

    # Mutually exclusive settings
    MUTUALLY_EXCLUSIVE = [
        ["magic_system.type", "technology.level"],  # High magic vs high tech
        ["society.government_type", "society.anarchy_level"],  # Government vs anarchy
    ]

    def __init__(self, bible_repo: IWorldBibleRepository):
        self._bible_repo = bible_repo

    def _flatten_dict(self, d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary with dot notation keys."""
        result = {}
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                result.update(self._flatten_dict(v, key))
            else:
                result[key] = v
        return result

    def _parse_settings(self, settings: TextContent) -> Dict[str, Any]:
        """Parse settings TextContent to dict."""
        try:
            content = settings.content
            if not content:
                return {}
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    def check_setting_conflicts(
        self,
        current_settings: TextContent,
        proposed_changes: Dict[str, Any],
    ) -> List[SettingConflict]:
        """Check for conflicts between current settings and proposed changes."""
        conflicts = []
        current = self._flatten_dict(self._parse_settings(current_settings))

        for field_path, new_value in proposed_changes.items():
            existing_value = self._get_nested_value(current, field_path)

            # Direct contradiction check
            if existing_value is not None and existing_value != new_value:
                conflicts.append(SettingConflict(
                    conflict_type=SettingConflictType.DIRECT_CONTRADICTION,
                    field_path=field_path,
                    existing_value=existing_value,
                    new_value=new_value,
                    description=f"Field '{field_path}' already has value '{existing_value}', proposing '{new_value}'",
                    severity="error",
                ))

            # Dependency check
            if field_path in self.SETTING_DEPENDENCIES:
                for dep in self.SETTING_DEPENDENCIES[field_path]:
                    dep_value = self._get_nested_value(current, dep)
                    if dep_value is None:
                        conflicts.append(SettingConflict(
                            conflict_type=SettingConflictType.MISSING_DEPENDENCY,
                            field_path=field_path,
                            existing_value=dep_value,
                            new_value=new_value,
                            description=f"Setting '{field_path}' requires '{dep}' to be set first",
                            severity="warning",
                        ))

            # Mutual exclusivity check
            for group in self.MUTUALLY_EXCLUSIVE:
                if field_path in group:
                    for other in group:
                        if other != field_path:
                            other_value = self._get_nested_value(current, other)
                            if other_value is not None:
                                conflicts.append(SettingConflict(
                                    conflict_type=SettingConflictType.SEMANTIC_CONFLICT,
                                    field_path=field_path,
                                    existing_value=other_value,
                                    new_value=new_value,
                                    description=f"'{field_path}' may conflict with '{other}' (mutually exclusive settings)",
                                    severity="warning",
                                ))

        return conflicts

    def _get_nested_value(self, d: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation path."""
        parts = path.split(".")
        current = d
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def check_lore_consistency(
        self,
        current_lore: List[Lore],
        new_lore: Lore,
    ) -> List[SettingConflict]:
        """Check new lore entry against existing lore for conflicts."""
        conflicts = []

        for existing in current_lore:
            # Check for duplicate titles in same category
            if existing.category == new_lore.category and existing.title.lower() == new_lore.title.lower():
                conflicts.append(SettingConflict(
                    conflict_type=SettingConflictType.DIRECT_CONTRADICTION,
                    field_path=f"lore.{new_lore.category}.{new_lore.title}",
                    existing_value=existing.content.content,
                    new_value=new_lore.content.content,
                    description=f"Lore entry '{new_lore.title}' already exists in category '{new_lore.category}'",
                    severity="error",
                ))

            # Check for contradictory content (simple keyword overlap with opposite sentiment)
            if existing.category == new_lore.category:
                existing_keywords = self._extract_keywords(existing.content.content)
                new_keywords = self._extract_keywords(new_lore.content.content)

                # Check for direct contradictions
                for kw in existing_keywords:
                    opposite = self._get_opposite(kw)
                    if opposite and opposite in new_keywords:
                        conflicts.append(SettingConflict(
                            conflict_type=SettingConflictType.SEMANTIC_CONFLICT,
                            field_path=f"lore.{new_lore.category}.{new_lore.title}",
                            existing_value=kw,
                            new_value=opposite,
                            description=f"Possible contradiction: '{kw}' vs '{opposite}' in {new_lore.category}",
                            severity="warning",
                        ))

        return conflicts

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        # Simple extraction - in reality would use NLP
        words = re.findall(r'[一-龯ァ-ヴーa-zA-Z]{2,}', text)
        return {w.lower() for w in words if len(w) > 2}

    def _get_opposite(self, word: str) -> Optional[str]:
        """Get opposite word for contradiction detection."""
        opposites = {
            "生": "死", "生きる": "死ぬ", "存在": "不在", "真実": "嘘",
            "光": "闇", "善": "悪", "平和": "戦争", "愛": "憎しみ",
            "自由": "束縛", "強い": "弱い", "古い": "新しい",
        }
        return opposites.get(word)

    async def full_consistency_check(self, novel_id: NovelId) -> ConsistencyReport:
        """Perform full consistency check on world bible."""
        bible = await self._bible_repo.get_by_novel(novel_id)
        if not bible:
            return ConsistencyReport(
                is_consistent=False,
                conflicts=[SettingConflict(
                    conflict_type=SettingConflictType.DIRECT_CONTRADICTION,
                    field_path="bible",
                    existing_value=None,
                    new_value=None,
                    description="World bible not found",
                    severity="critical",
                )],
                warnings=[],
                suggestions=["Create world bible first"],
                checked_settings=0,
                checked_lore=0,
            )

        all_conflicts = []
        warnings = []
        suggestions = []

        # Check settings internal consistency
        settings_dict = self._parse_settings(bible.settings)
        flat_settings = self._flatten_dict(settings_dict)

        # Check for circular dependencies
        circular = self._detect_circular_dependencies(flat_settings)
        for cycle in circular:
            all_conflicts.append(SettingConflict(
                conflict_type=SettingConflictType.CIRCULAR_DEPENDENCY,
                field_path=" -> ".join(cycle),
                existing_value=cycle[0],
                new_value=cycle[-1],
                description=f"Circular dependency detected: {' -> '.join(cycle)}",
                severity="error",
            ))

        # Check revealed vs unrevealed consistency
        revealed_dict = self._parse_settings(bible.revealed)
        for key, value in revealed_dict.items():
            if key in flat_settings and flat_settings[key] != value:
                all_conflicts.append(SettingConflict(
                    conflict_type=SettingConflictType.INCONSISTENT_VALUE,
                    field_path=f"revealed.{key}",
                    existing_value=flat_settings[key],
                    new_value=value,
                    description=f"Revealed value differs from actual setting: '{key}'",
                    severity="warning",
                ))

        # Check pending settings
        for field_name, pending in bible.get_pending_settings().items():
            if field_name in flat_settings:
                if flat_settings[field_name] != pending.proposed_value.content:
                    warnings.append(f"Pending setting '{field_name}' differs from current value")

        # Check lore consistency
        all_lore = await self._bible_repo.get_all_lore(novel_id)
        for lore in all_lore:
            conflicts = self.check_lore_consistency(all_lore, lore)
            all_conflicts.extend(conflicts)

        is_consistent = not any(c.severity in ("error", "critical") for c in all_conflicts)

        # Generate suggestions
        if all_conflicts:
            suggestions.append("Review and resolve detected conflicts")
        if not bible.settings.content:
            suggestions.append("World bible settings are empty - consider initializing with default template")
        if len(all_lore) < 5:
            suggestions.append("Consider adding more lore entries for richer worldbuilding")

        return ConsistencyReport(
            is_consistent=is_consistent,
            conflicts=all_conflicts,
            warnings=warnings,
            suggestions=suggestions,
            checked_settings=len(flat_settings),
            checked_lore=len(all_lore),
        )

    def _detect_circular_dependencies(self, settings: Dict[str, Any]) -> List[List[str]]:
        """Detect circular dependencies in settings."""
        graph = {}
        for key in settings:
            if key in self.SETTING_DEPENDENCIES:
                graph[key] = self.SETTING_DEPENDENCIES[key]

        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles


class BibleValidator:
    """Validates world bible entities."""

    @staticmethod
    def validate_world_bible(bible: WorldBible) -> List[str]:
        """Validate world bible. Returns list of errors."""
        errors = []

        if not bible.novel_id:
            errors.append("Novel ID is required")

        if bible.version < 1:
            errors.append("Version must be >= 1")

        return errors

    @staticmethod
    def validate_setting(setting: Setting) -> List[str]:
        """Validate setting entry."""
        errors = []

        if not setting.name.strip():
            errors.append("Setting name cannot be empty")

        if not setting.category.strip():
            errors.append("Setting category cannot be empty")

        return errors

    @staticmethod
    def validate_lore(lore: Lore) -> List[str]:
        """Validate lore entry."""
        errors = []

        if not lore.title.strip():
            errors.append("Lore title cannot be empty")

        if not lore.category.strip():
            errors.append("Lore category cannot be empty")

        return errors


@dataclass
class BibleDomainService:
    """
    Domain service for world bible business logic.

    Pure business logic - no infrastructure dependencies.
    Depends only on repository interfaces.
    """
    bible_repo: IWorldBibleRepository

    def __post_init__(self):
        self._validator = BibleValidator()
        self._consistency_checker = BibleConsistencyChecker(self.bible_repo)

    async def create_world_bible(self, novel_id: NovelId) -> WorldBible:
        """Create a new world bible for a novel."""
        existing = await self.bible_repo.get_by_novel(novel_id)
        if existing:
            raise BibleValidationError(f"World bible for novel {novel_id} already exists")

        bible = WorldBible.create(novel_id)
        return await self.bible_repo.save(bible)

    async def get_world_bible(self, novel_id: NovelId) -> Optional[WorldBible]:
        """Get world bible by novel ID."""
        return await self.bible_repo.get_by_novel(novel_id)

    async def update_settings(
        self,
        novel_id: NovelId,
        settings: TextContent,
        increment_version: bool = True,
    ) -> WorldBible:
        """Update world bible settings."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        bible.update_settings(settings, increment_version)

        errors = self._validator.validate_world_bible(bible)
        if errors:
            raise BibleValidationError("; ".join(errors))

        return await self.bible_repo.save(bible)

    async def update_revealed(
        self,
        novel_id: NovelId,
        revealed: TextContent,
    ) -> WorldBible:
        """Update revealed information."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        bible.update_revealed(revealed)
        return await self.bible_repo.save(bible)

    async def propose_setting_change(
        self,
        novel_id: NovelId,
        field_name: str,
        proposed_value: TextContent,
        confidence: float = 0.0,
    ) -> PendingSetting:
        """Propose a setting change for review."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        if not 0.0 <= confidence <= 1.0:
            raise BibleValidationError("Confidence must be between 0.0 and 1.0")

        bible.add_pending_setting(field_name, proposed_value, confidence)
        return await self.bible_repo.save(bible)

    async def confirm_pending_setting(self, novel_id: NovelId, field_name: str) -> Optional[PendingSetting]:
        """Confirm a pending setting."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        pending = bible.confirm_pending_setting(field_name)
        if pending:
            await self.bible_repo.save(bible)
        return pending

    async def reject_pending_setting(self, novel_id: NovelId, field_name: str) -> Optional[PendingSetting]:
        """Reject a pending setting."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        pending = bible.reject_pending_setting(field_name)
        if pending:
            await self.bible_repo.save(bible)
        return pending

    async def get_pending_settings(self, novel_id: NovelId) -> List[PendingSetting]:
        """Get all pending settings."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            return []
        return bible.get_pending_settings()

    async def add_setting(
        self,
        novel_id: NovelId,
        name: str,
        value: TextContent,
        category: str,
    ) -> Setting:
        """Add a new setting entry."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        setting = Setting(
            id=SettingId.generate(),
            name=name,
            value=value,
            category=category,
        )

        errors = self._validator.validate_setting(setting)
        if errors:
            raise BibleValidationError("; ".join(errors))

        # In real implementation, would add to bible.settings structure
        return await self.bible_repo.save_setting(novel_id, setting)

    async def update_setting(
        self,
        novel_id: NovelId,
        setting_id: SettingId,
        value: TextContent,
    ) -> Setting:
        """Update a setting entry."""
        setting = await self.bible_repo.get_setting(novel_id, setting_id)
        if not setting:
            raise BibleValidationError(f"Setting {setting_id} not found")

        updated = setting.update_value(value)
        return await self.bible_repo.save_setting(novel_id, updated)

    async def reveal_setting(self, novel_id: NovelId, setting_id: SettingId) -> Setting:
        """Mark a setting as revealed to readers."""
        setting = await self.bible_repo.get_setting(novel_id, setting_id)
        if not setting:
            raise BibleValidationError(f"Setting {setting_id} not found")

        revealed = setting.mark_revealed()
        return await self.bible_repo.save_setting(novel_id, revealed)

    async def create_lore(
        self,
        novel_id: NovelId,
        title: str,
        content: TextContent,
        category: str,
        tags: Optional[List[str]] = None,
        is_secret: bool = False,
    ) -> Lore:
        """Create a new lore entry."""
        lore = Lore.create(
            novel_id=novel_id,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            is_secret=is_secret,
        )

        errors = self._validator.validate_lore(lore)
        if errors:
            raise BibleValidationError("; ".join(errors))

        # Check consistency with existing lore
        existing_lore = await self.bible_repo.get_all_lore(novel_id)
        conflicts = self._consistency_checker.check_lore_consistency(existing_lore, lore)
        critical_conflicts = [c for c in conflicts if c.severity in ("error", "critical")]
        if critical_conflicts:
            raise BibleValidationError(f"Lore conflicts detected: {', '.join(c.description for c in critical_conflicts)}")

        return await self.bible_repo.save_lore(novel_id, lore)

    async def update_lore(
        self,
        novel_id: NovelId,
        lore_id: SettingId,
        content: Optional[TextContent] = None,
        tags: Optional[List[str]] = None,
    ) -> Lore:
        """Update a lore entry."""
        lore = await self.bible_repo.get_lore(novel_id, lore_id)
        if not lore:
            raise BibleValidationError(f"Lore {lore_id} not found")

        if content is not None:
            lore = Lore(
                id=lore.id,
                novel_id=lore.novel_id,
                title=lore.title,
                content=content,
                category=lore.category,
                tags=lore.tags,
                is_secret=lore.is_secret,
                created_at=lore.created_at,
                updated_at=datetime.now(),
            )

        if tags is not None:
            lore = Lore(
                id=lore.id,
                novel_id=lore.novel_id,
                title=lore.title,
                content=lore.content,
                category=lore.category,
                tags=tags,
                is_secret=lore.is_secret,
                created_at=lore.created_at,
                updated_at=datetime.now(),
            )

        return await self.bible_repo.save_lore(novel_id, lore)

    async def add_lore_tag(self, novel_id: NovelId, lore_id: SettingId, tag: str) -> Lore:
        """Add a tag to lore entry."""
        lore = await self.bible_repo.get_lore(novel_id, lore_id)
        if not lore:
            raise BibleValidationError(f"Lore {lore_id} not found")

        updated = lore.add_tag(tag)
        return await self.bible_repo.save_lore(novel_id, updated)

    async def get_all_lore(self, novel_id: NovelId) -> List[Lore]:
        """Get all lore entries for a novel."""
        return await self.bible_repo.get_all_lore(novel_id)

    async def get_lore_by_category(self, novel_id: NovelId, category: str) -> List[Lore]:
        """Get lore entries by category."""
        all_lore = await self.bible_repo.get_all_lore(novel_id)
        return [l for l in all_lore if l.category == category]

    async def check_consistency(self, novel_id: NovelId) -> ConsistencyReport:
        """Perform full consistency check."""
        return await self._consistency_checker.full_consistency_check(novel_id)

    async def check_setting_conflicts(
        self,
        novel_id: NovelId,
        proposed_changes: Dict[str, Any],
    ) -> List[SettingConflict]:
        """Check proposed changes against current settings for conflicts."""
        bible = await self.bible_repo.get_by_novel(novel_id)
        if not bible:
            raise BibleValidationError(f"World bible for novel {novel_id} not found")

        return self._consistency_checker.check_setting_conflicts(bible.settings, proposed_changes)

    async def delete_setting(self, novel_id: NovelId, setting_id: SettingId) -> bool:
        """Delete a setting."""
        return await self.bible_repo.delete_setting(novel_id, setting_id)

    async def delete_lore(self, novel_id: NovelId, lore_id: SettingId) -> bool:
        """Delete a lore entry."""
        return await self.bible_repo.delete_lore(novel_id, lore_id)

    async def create_setting_snapshot(
        self,
        novel_id: NovelId,
        change_summary: str = "",
        created_by: Optional[str] = None,
    ) -> int:
        """Create a settings version snapshot."""
        return await self.bible_repo.create_setting_snapshot(novel_id, change_summary, created_by)

    async def get_setting_history(self, novel_id: NovelId) -> List[Dict[str, Any]]:
        """Get setting version history."""
        return await self.bible_repo.get_setting_history(novel_id)

    async def restore_setting_version(self, novel_id: NovelId, version_id: int) -> WorldBible:
        """Restore a previous setting version."""
        bible = await self.bible_repo.restore_setting_version(novel_id, version_id)
        if not bible:
            raise BibleValidationError(f"Setting version {version_id} not found")
        return await self.bible_repo.save(bible)


import re
