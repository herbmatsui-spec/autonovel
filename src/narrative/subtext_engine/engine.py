"""
SubtextEngine: Core deterministic rewrite engine for narrative dialogue.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.narrative.subtext_engine.models import (
    DialogueBlock,
    RewriteResult,
    RewriteRuleModel,
    SubtextContext,
)
from src.narrative.subtext_engine.rules import (
    AddressDistanceRule,
    CausalToIronyRule,
    ComplianceSubvertRule,
    EmotionToActionRule,
    ExplanatoryCompressRule,
    RegexRule,
    RuleBase,
    RuleRegistry,
    SubjectiveInternalizeRule,
    ThreatSubtextRule,
    create_extension_rules,
)

logger = logging.getLogger("narrative.subtext_engine")


class SubtextEngine:
    """Deterministic rewrite engine applying subtext rules to dialogue blocks."""

    def __init__(
        self,
        registry: Optional[RuleRegistry] = None,
        debug_mode: bool = False,
        debug_log_path: Optional[str] = None,
    ) -> None:
        self.registry = registry or RuleRegistry.get_instance()
        self.debug_mode = debug_mode
        self.debug_log_path = debug_log_path

        # Statistics tracker (Step 22)
        self._stats: Dict[str, Any] = {
            "total_blocks_processed": 0,
            "modified_blocks_count": 0,
            "rule_application_counts": {},
            "total_chars_before": 0,
            "total_chars_after": 0,
            "beats_inserted_count": 0,
            "processing_time_ms": 0.0,
        }

    @classmethod
    def create_default(cls, debug_mode: bool = False) -> SubtextEngine:
        """Instantiates engine with default core rules and extension rules registered."""
        registry = RuleRegistry()
        # Core rules 1-7
        registry.register(ExplanatoryCompressRule())
        registry.register(EmotionToActionRule())
        registry.register(CausalToIronyRule())
        registry.register(SubjectiveInternalizeRule())
        registry.register(ThreatSubtextRule())
        registry.register(ComplianceSubvertRule())
        registry.register(AddressDistanceRule())

        # Extension rules 8-15
        for ext_rule in create_extension_rules():
            registry.register(ext_rule)

        return cls(registry=registry, debug_mode=debug_mode)

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path], debug_mode: bool = False) -> SubtextEngine:
        """Loads rules from a YAML configuration file (Step 6)."""
        registry = RuleRegistry()
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"Config file not found: {path}. Falling back to default rules.")
            return cls.create_default(debug_mode=debug_mode)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to read YAML rules from {path}: {e}. Falling back to default.")
            return cls.create_default(debug_mode=debug_mode)

        rules_list = data.get("rules", [])
        for r_spec in rules_list:
            r_id = r_spec.get("id")
            pattern = r_spec.get("pattern")
            replacement = r_spec.get("replacement", "")
            if not r_id or not pattern:
                continue

            rule = RegexRule(
                rule_id=r_id,
                pattern=pattern,
                replacement=replacement,
                name=r_spec.get("name", r_id),
                priority=r_spec.get("priority", 100),
                final=r_spec.get("final", False),
                skip_if_matched=r_spec.get("skip_if_matched", False),
                enabled=r_spec.get("enabled", True),
                tags=r_spec.get("tags", []),
                description=r_spec.get("description", ""),
            )
            registry.register(rule)

        return cls(registry=registry, debug_mode=debug_mode)

    def process_block(
        self,
        block: DialogueBlock,
        context: Optional[SubtextContext] = None,
    ) -> DialogueBlock:
        """Processes a single DialogueBlock through registered rules in priority order."""
        current_block = block.clone()
        rules = self.registry.list_rules(enabled_only=True)

        for rule in rules:
            try:
                result = rule.apply(current_block, context=context)
                if result.modified:
                    current_block = result.block
                    # Track statistics
                    rule_id = rule.id
                    self._stats["rule_application_counts"][rule_id] = (
                        self._stats["rule_application_counts"].get(rule_id, 0) + 1
                    )
                    # Check if final flag is set
                    if rule.final:
                        break
            except Exception as e:
                # Step 19: Safe fallback on rule exception
                logger.warning(f"Exception during rule {rule.id} execution: {e}. Keeping current text.")
                continue

        return current_block

    def process(
        self,
        blocks: List[DialogueBlock],
        context: Optional[SubtextContext] = None,
    ) -> List[DialogueBlock]:
        """Step 5: Processes a list of DialogueBlocks in order with statistics and logging."""
        start_time = time.perf_counter()
        processed_blocks: List[DialogueBlock] = []

        for block in blocks:
            text_before = block.raw_text()
            self._stats["total_blocks_processed"] += 1
            self._stats["total_chars_before"] += len(text_before)

            new_block = self.process_block(block, context=context)
            text_after = new_block.raw_text()
            self._stats["total_chars_after"] += len(text_after)

            is_modified = text_before != text_after
            if is_modified:
                self._stats["modified_blocks_count"] += 1
                if "（" in text_after or "——" in text_after:
                    self._stats["beats_inserted_count"] += 1

                # Step 16: Debug logging / diff recording
                if self.debug_mode:
                    self._log_diff(block, new_block)

            processed_blocks.append(new_block)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self._stats["processing_time_ms"] += elapsed_ms
        return processed_blocks

    def _log_diff(self, before: DialogueBlock, after: DialogueBlock) -> None:
        """Step 16: Outputs diff and JSONL record when debug_mode is active."""
        diff_lines = list(
            difflib.unified_diff(
                before.lines,
                after.lines,
                fromfile="before",
                tofile="after",
                lineterm="",
            )
        )
        record = {
            "speaker": before.speaker,
            "rules_applied": after.applied_rules,
            "before_lines": before.lines,
            "after_lines": after.lines,
            "diff": diff_lines,
        }

        if self.debug_log_path:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.debug_log_path)), exist_ok=True)
                with open(self.debug_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"Failed to write debug log to {self.debug_log_path}: {e}")
        else:
            logger.debug(f"SubtextEngine Diff: {json.dumps(record, ensure_ascii=False)}")

    def generate_report(self) -> Dict[str, Any]:
        """Step 22: Returns aggregated statistics report."""
        chars_reduced = self._stats["total_chars_before"] - self._stats["total_chars_after"]
        return {
            "total_blocks_processed": self._stats["total_blocks_processed"],
            "modified_blocks_count": self._stats["modified_blocks_count"],
            "modification_rate": (
                (self._stats["modified_blocks_count"] / self._stats["total_blocks_processed"])
                if self._stats["total_blocks_processed"] > 0
                else 0.0
            ),
            "rule_application_counts": dict(self._stats["rule_application_counts"]),
            "chars_reduced": chars_reduced,
            "beats_inserted_count": self._stats["beats_inserted_count"],
            "processing_time_ms": round(self._stats["processing_time_ms"], 3),
        }

    def reset_stats(self) -> None:
        """Resets the statistics counters."""
        self._stats = {
            "total_blocks_processed": 0,
            "modified_blocks_count": 0,
            "rule_application_counts": {},
            "total_chars_before": 0,
            "total_chars_after": 0,
            "beats_inserted_count": 0,
            "processing_time_ms": 0.0,
        }

    def detect_conflicts(
        self, sample_blocks: List[DialogueBlock]
    ) -> List[Dict[str, Any]]:
        """Step 21: Detects rules that match the same block and could conflict."""
        conflicts = []
        rules = self.registry.list_rules(enabled_only=True)

        for block in sample_blocks:
            matching_rules = []
            for rule in rules:
                res = rule.apply(block.clone())
                if res.modified:
                    matching_rules.append(rule.id)

            if len(matching_rules) > 1:
                conflicts.append({
                    "speaker": block.speaker,
                    "text": block.raw_text(),
                    "matching_rules": matching_rules,
                })

        return conflicts
