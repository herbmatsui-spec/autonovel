"""Character domain service - pure business logic for character consistency and relationship validation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from collections import defaultdict

from src.domain.entities.character import Character, CharacterArc
from src.domain.value_objects.ids import NovelId, CharacterId
from src.domain.value_objects.metadata import CharacterMetadata
from src.domain.repositories.character_repository import ICharacterRepository


class CharacterValidationError(Exception):
    """Raised when character validation fails."""
    pass


class RelationshipType(Enum):
    """Types of character relationships."""
    ALLY = "ally"
    ENEMY = "enemy"
    ROMANTIC = "romantic"
    FAMILY = "family"
    RIVAL = "rival"
    MENTOR = "mentor"
    SUBORDINATE = "subordinate"
    NEUTRAL = "neutral"


@dataclass
class CharacterRelationship:
    """Represents a relationship between two characters."""
    character_id: CharacterId
    target_id: CharacterId
    relationship_type: RelationshipType
    strength: int = 50  # 0-100
    description: str = ""
    is_mutual: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CharacterConsistencyIssue:
    """Represents a consistency issue with a character."""
    issue_type: str
    field: str
    description: str
    severity: str = "warning"  # info, warning, error
    episode_number: int = 0


class CharacterValidator:
    """Validates character entities."""

    @staticmethod
    def validate_character(character: Character) -> List[str]:
        """Validate character. Returns list of errors."""
        errors = []

        if not character.name.strip():
            errors.append("Character name cannot be empty")

        if not character.role.strip():
            errors.append("Character role cannot be empty")

        if character.novel_id is None:
            errors.append("Novel ID is required")

        return errors

    @staticmethod
    def validate_character_arc(arc: CharacterArc) -> List[str]:
        """Validate character arc."""
        errors = []

        if not arc.arc_name.strip():
            errors.append("Arc name cannot be empty")

        if not arc.arc_stages:
            errors.append("Arc must have at least one stage")

        if arc.current_stage_index < 0:
            errors.append("Current stage index cannot be negative")

        if arc.current_stage_index >= len(arc.arc_stages):
            errors.append("Current stage index out of bounds")

        return errors


class CharacterConsistencyChecker:
    """Checks character consistency across episodes and arcs."""

    def __init__(self, char_repo: ICharacterRepository):
        self._char_repo = char_repo

    async def check_character_consistency(
        self,
        novel_id: NovelId,
        character_id: CharacterId,
    ) -> List[CharacterConsistencyIssue]:
        """Check character consistency across all appearances."""
        issues = []

        character = await self._char_repo.get_by_id(character_id)
        if not character:
            issues.append(CharacterConsistencyIssue(
                issue_type="not_found",
                field="character",
                description=f"Character {character_id} not found",
                severity="error",
            ))
            return issues

        # Check arcs consistency
        arcs = character.get_arcs()
        for arc in arcs:
            arc_issues = self._check_arc_consistency(character, arc)
            issues.extend(arc_issues)

        # Check for duplicate roles in same novel
        all_chars = await self._char_repo.list_by_novel(novel_id)
        role_counts = defaultdict(int)
        for c in all_chars:
            role_counts[c.role] += 1

        if role_counts[character.role] > 1:
            issues.append(CharacterConsistencyIssue(
                issue_type="duplicate_role",
                field="role",
                description=f"Multiple characters have role '{character.role}' in this novel",
                severity="warning",
            ))

        return issues

    def _check_arc_consistency(
        self,
        character: Character,
        arc: CharacterArc,
    ) -> List[CharacterConsistencyIssue]:
        """Check character arc consistency."""
        issues = []

        if arc.character_id != character.id:
            issues.append(CharacterConsistencyIssue(
                issue_type="arc_mismatch",
                field="character_id",
                description=f"Arc character_id ({arc.character_id}) doesn't match character ({character.id})",
                severity="error",
            ))

        if arc.novel_id != character.novel_id:
            issues.append(CharacterConsistencyIssue(
                issue_type="arc_mismatch",
                field="novel_id",
                description=f"Arc novel_id ({arc.novel_id}) doesn't match character ({character.novel_id})",
                severity="error",
            ))

        if arc.is_completed and arc.current_stage_index < len(arc.arc_stages) - 1:
            issues.append(CharacterConsistencyIssue(
                issue_type="arc_incomplete",
                field="is_completed",
                description="Arc marked complete but not all stages finished",
                severity="warning",
            ))

        return issues

    async def check_relationship_consistency(
        self,
        novel_id: NovelId,
    ) -> List[CharacterConsistencyIssue]:
        """Check all character relationships for consistency."""
        issues = []
        all_chars = await self._char_repo.list_by_novel(novel_id)

        # Build relationship map
        defaultdict(list)

        for char in all_chars:
            # In real implementation, would fetch from relationship repository
            pass

        return issues


class CharacterRelationshipManager:
    """Manages character relationships."""

    def __init__(self):
        self._relationships: Dict[CharacterId, List[CharacterRelationship]] = defaultdict(list)

    def add_relationship(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
        relationship_type: RelationshipType,
        strength: int = 50,
        description: str = "",
        is_mutual: bool = True,
    ) -> CharacterRelationship:
        """Add a relationship."""
        if not 0 <= strength <= 100:
            raise ValueError("Strength must be between 0 and 100")

        rel = CharacterRelationship(
            character_id=character_id,
            target_id=target_id,
            relationship_type=relationship_type,
            strength=strength,
            description=description,
            is_mutual=is_mutual,
        )

        self._relationships[character_id].append(rel)

        if is_mutual:
            # Add reverse relationship
            reverse_type = self._get_reverse_type(relationship_type)
            reverse_rel = CharacterRelationship(
                character_id=target_id,
                target_id=character_id,
                relationship_type=reverse_type,
                strength=strength,
                description=description,
                is_mutual=True,
            )
            self._relationships[target_id].append(reverse_rel)

        return rel

    def _get_reverse_type(self, rel_type: RelationshipType) -> RelationshipType:
        """Get reverse relationship type."""
        reverse_map = {
            RelationshipType.ALLY: RelationshipType.ALLY,
            RelationshipType.ENEMY: RelationshipType.ENEMY,
            RelationshipType.ROMANTIC: RelationshipType.ROMANTIC,
            RelationshipType.FAMILY: RelationshipType.FAMILY,
            RelationshipType.RIVAL: RelationshipType.RIVAL,
            RelationshipType.MENTOR: RelationshipType.SUBORDINATE,
            RelationshipType.SUBORDINATE: RelationshipType.MENTOR,
            RelationshipType.NEUTRAL: RelationshipType.NEUTRAL,
        }
        return reverse_map.get(rel_type, RelationshipType.NEUTRAL)

    def get_relationships(self, character_id: CharacterId) -> List[CharacterRelationship]:
        """Get all relationships for a character."""
        return self._relationships.get(character_id, [])

    def get_relationship(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
    ) -> Optional[CharacterRelationship]:
        """Get specific relationship."""
        for rel in self._relationships.get(character_id, []):
            if rel.target_id == target_id:
                return rel
        return None

    def update_relationship_strength(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
        strength: int,
    ) -> bool:
        """Update relationship strength."""
        if not 0 <= strength <= 100:
            raise ValueError("Strength must be between 0 and 100")

        for rel in self._relationships.get(character_id, []):
            if rel.target_id == target_id:
                rel.strength = strength
                return True
        return False

    def remove_relationship(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
    ) -> bool:
        """Remove a relationship."""
        rels = self._relationships.get(character_id, [])
        for i, rel in enumerate(rels):
            if rel.target_id == target_id:
                rels.pop(i)
                # Also remove reverse if mutual
                if rel.is_mutual:
                    self.remove_relationship(target_id, character_id)
                return True
        return False


@dataclass
class CharacterDomainService:
    """
    Domain service for character business logic.

    Pure business logic - no infrastructure dependencies.
    Depends only on repository interfaces.
    """
    character_repo: ICharacterRepository

    def __post_init__(self):
        self._validator = CharacterValidator()
        self._consistency_checker = CharacterConsistencyChecker(self.character_repo)
        self._relationship_manager = CharacterRelationshipManager()

    async def create_character(
        self,
        novel_id: NovelId,
        name: str,
        role: str,
        personality: str = "",
        ability: str = "",
    ) -> Character:
        """Create a new character."""
        character = Character.create(
            novel_id=novel_id,
            name=name,
            role=role,
            personality=personality,
            ability=ability,
        )

        errors = self._validator.validate_character(character)
        if errors:
            raise CharacterValidationError("; ".join(errors))

        return await self.character_repo.save(character)

    async def get_character(self, character_id: CharacterId) -> Optional[Character]:
        """Get character by ID."""
        return await self.character_repo.get_by_id(character_id)

    async def get_character_by_name(self, novel_id: NovelId, name: str) -> Optional[Character]:
        """Get character by name within a novel."""
        return await self.character_repo.get_by_name(novel_id, name)

    async def update_character(
        self,
        character_id: CharacterId,
        name: Optional[str] = None,
        role: Optional[str] = None,
        personality: Optional[str] = None,
        ability: Optional[str] = None,
        registry_data: Optional[str] = None,
    ) -> Character:
        """Update character details."""
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            raise CharacterValidationError(f"Character {character_id} not found")

        character.update_details(
            name=name,
            role=role,
            personality=personality,
            ability=ability,
            registry_data=registry_data,
        )

        errors = self._validator.validate_character(character)
        if errors:
            raise CharacterValidationError("; ".join(errors))

        return await self.character_repo.save(character)

    async def list_characters(self, novel_id: NovelId) -> List[Character]:
        """List all characters in a novel."""
        return await self.character_repo.list_by_novel(novel_id)

    async def delete_character(self, character_id: CharacterId) -> bool:
        """Delete a character."""
        return await self.character_repo.delete(character_id)

    async def create_character_arc(
        self,
        novel_id: NovelId,
        character_id: CharacterId,
        arc_name: str,
        stages: List[str],
    ) -> CharacterArc:
        """Create a new character arc."""
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            raise CharacterValidationError(f"Character {character_id} not found")

        arc = CharacterArc.create(
            novel_id=novel_id,
            character_id=character_id,
            arc_name=arc_name,
            stages=stages,
        )

        errors = self._validator.validate_character_arc(arc)
        if errors:
            raise CharacterValidationError("; ".join(errors))

        character.add_arc(arc)
        await self.character_repo.save(character)
        return await self.character_repo.save_arc(arc)

    async def advance_character_arc(self, arc_id: CharacterId) -> CharacterArc:
        """Advance character arc to next stage."""
        arc = await self.character_repo.get_arc(arc_id)
        if not arc:
            raise CharacterValidationError(f"Character arc {arc_id} not found")

        arc.advance_stage()
        return await self.character_repo.save_arc(arc)

    async def get_character_arcs(self, character_id: CharacterId) -> List[CharacterArc]:
        """Get all arcs for a character."""
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            return []
        return character.get_arcs()

    async def get_current_arc(self, character_id: CharacterId) -> Optional[CharacterArc]:
        """Get current active arc for a character."""
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            return None
        return character.get_current_arc()

    async def check_consistency(self, novel_id: NovelId, character_id: CharacterId) -> List[CharacterConsistencyIssue]:
        """Check character consistency."""
        return await self._consistency_checker.check_character_consistency(novel_id, character_id)

    async def check_all_consistency(self, novel_id: NovelId) -> Dict[CharacterId, List[CharacterConsistencyIssue]]:
        """Check consistency for all characters in a novel."""
        characters = await self.character_repo.list_by_novel(novel_id)
        result = {}
        for char in characters:
            issues = await self._consistency_checker.check_character_consistency(novel_id, char.id)
            if issues:
                result[char.id] = issues
        return result

    # Relationship management
    def add_relationship(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
        relationship_type: RelationshipType,
        strength: int = 50,
        description: str = "",
        is_mutual: bool = True,
    ) -> CharacterRelationship:
        """Add a relationship between characters."""
        return self._relationship_manager.add_relationship(
            character_id, target_id, relationship_type, strength, description, is_mutual
        )

    def get_relationships(self, character_id: CharacterId) -> List[CharacterRelationship]:
        """Get all relationships for a character."""
        return self._relationship_manager.get_relationships(character_id)

    def get_relationship(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
    ) -> Optional[CharacterRelationship]:
        """Get specific relationship."""
        return self._relationship_manager.get_relationship(character_id, target_id)

    def update_relationship_strength(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
        strength: int,
    ) -> bool:
        """Update relationship strength."""
        return self._relationship_manager.update_relationship_strength(character_id, target_id, strength)

    def remove_relationship(
        self,
        character_id: CharacterId,
        target_id: CharacterId,
    ) -> bool:
        """Remove a relationship."""
        return self._relationship_manager.remove_relationship(character_id, target_id)

    async def get_character_with_relationships(
        self,
        character_id: CharacterId,
    ) -> Optional[Character]:
        """Get character with all relationships loaded."""
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            return None

        # Attach relationships (in real implementation, would be loaded from repo)
        character._relationships = self.get_relationships(character_id)
        return character

    async def get_character_metadata(self, character_id: CharacterId) -> Optional[CharacterMetadata]:
        """Get character metadata."""
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            return None
        return character.to_metadata()

    async def validate_new_character(
        self,
        novel_id: NovelId,
        name: str,
        role: str,
    ) -> List[str]:
        """Validate if a new character can be created without conflicts."""
        warnings = []

        # Check for duplicate name
        existing = await self.character_repo.get_by_name(novel_id, name)
        if existing:
            warnings.append(f"Character with name '{name}' already exists in this novel")

        # Check for duplicate main character role
        if role.lower() in ("protagonist", "main character", "hero", "heroine"):
            all_chars = await self.character_repo.list_by_novel(novel_id)
            for c in all_chars:
                if c.role.lower() in ("protagonist", "main character", "hero", "heroine"):
                    warnings.append(f"Novel already has a main character: {c.name}")

        return warnings
