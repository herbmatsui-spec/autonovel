"""
Data models for subtext rewrite engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SubtextContext(BaseModel):
    """Context information supplied to subtext rules, templates, and token expanders."""
    scene_id: str = Field(default="", description="Scene identifier")
    turn_index: int = Field(default=0, description="Dialogue turn index in scene")
    speaker: str = Field(default="", description="Speaking character name")
    target_speaker: str = Field(default="", description="Addressed character name")
    emotion: str = Field(default="neutral", description="Primary emotional state (e.g. betrayal, grief, anger)")
    power_dynamic: str = Field(default="equal", description="inferior, equal, superior")
    relationship: str = Field(default="neutral", description="former_ally, enemy, lover, subordinate, stranger")
    intensity: str = Field(default="medium", description="low, medium, high")
    genre: str = Field(default="general", description="Genre modifier (e.g. fantasy, horror, romance)")
    tone: str = Field(default="neutral", description="Tone modifier (e.g. dark, ironic, light)")
    history_summary: List[str] = Field(default_factory=list, description="Recent conversation turns or subtext history")
    relationship_graph: Dict[str, Any] = Field(default_factory=dict, description="Inter-character relationship properties")
    custom: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extension parameters")


class DialogueBlock(BaseModel):
    """Represents a block of dialogue and stage directions from a speaker."""
    speaker: str = Field(default="", description="Speaker identifier or empty for narrative/stage beat")
    lines: List[str] = Field(default_factory=list, description="Lines of dialogue or stage directions")
    context: Dict[str, Any] = Field(default_factory=dict, description="Block-specific contextual tags")
    applied_rules: List[str] = Field(default_factory=list, description="IDs of rules applied to this block")

    def raw_text(self) -> str:
        """Returns the joined lines as text."""
        return "\n".join(self.lines)

    def clone(self) -> DialogueBlock:
        """Creates a deep copy of the block."""
        return DialogueBlock(
            speaker=self.speaker,
            lines=list(self.lines),
            context=dict(self.context),
            applied_rules=list(self.applied_rules)
        )


class RewriteRuleModel(BaseModel):
    """Serializable specification of a rewrite rule."""
    id: str = Field(..., description="Unique rule ID")
    name: str = Field(default="", description="Human-readable rule name")
    pattern: str = Field(..., description="Regular expression pattern")
    replacement: str = Field(default="", description="Replacement pattern or template")
    priority: int = Field(default=100, description="Execution priority (lower executes earlier)")
    final: bool = Field(default=False, description="Whether matching stops subsequent rules")
    skip_if_matched: bool = Field(default=False, description="Skip if specific context tags already matched")
    enabled: bool = Field(default=True, description="Enable or disable the rule")
    tags: List[str] = Field(default_factory=list, description="Rule tags for categorization")
    description: str = Field(default="", description="Detailed description")


class RewriteResult(BaseModel):
    """Result of applying one or more rewrite rules."""
    success: bool = True
    modified: bool = False
    block: DialogueBlock
    applied_rule_id: Optional[str] = None
    diff_summary: str = ""
