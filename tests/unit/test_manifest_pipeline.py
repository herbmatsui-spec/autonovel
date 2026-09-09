"""Tests for Skill-Driven Dynamic Pipeline via manifest.yaml (Phase 2 / Steps 13-24)."""
import pytest
import tempfile
import os
import yaml
from unittest.mock import MagicMock, AsyncMock

from src.agents.skill_base import (
    SkillAgent,
    SkillManifest,
    SkillManifestItem,
    validate_manifest,
    load_skill_from_spec,
)
from src.agents.orchestrator import (
    Orchestrator,
    AgentContext,
    AgentResult,
    CyclicDependencyError,
)


class DummyStepSkill(SkillAgent):
    """テスト用のシンプルなスキル"""
    async def execute(self, ctx: AgentContext) -> AgentResult:
        execution_order = ctx.artifacts.setdefault("execution_order", [])
        execution_order.append(self._skill_name)
        return AgentResult(next_agent=None, artifacts={"execution_order": execution_order})


@pytest.mark.asyncio
async def test_manifest_validation():
    """Step 13: Manifest Pydantic validation checks required fields and errors on invalid data."""
    valid_data = {
        "skills": [
            {
                "name": "Dummy1",
                "class": "tests.unit.test_manifest_pipeline.DummyStepSkill",
                "depends_on": [],
                "runs_after": [],
                "runs_before": [],
                "config": {"enabled": True},
            }
        ]
    }
    manifest = validate_manifest(valid_data)
    assert len(manifest.skills) == 1
    assert manifest.skills[0].name == "Dummy1"

    # Invalid: missing 'skills' key
    with pytest.raises(ValueError):
        validate_manifest({"invalid": 123})


def test_cyclic_dependency_detection():
    """Step 15: Cyclic dependency raises CyclicDependencyError."""
    orch = Orchestrator(nodes={})
    cyclic_manifest = [
        {"name": "SkillA", "runs_after": ["SkillB"]},
        {"name": "SkillB", "runs_after": ["SkillC"]},
        {"name": "SkillC", "runs_after": ["SkillA"]},
    ]
    with pytest.raises(CyclicDependencyError) as exc_info:
        orch.build_execution_order(cyclic_manifest, available_skills=None)
    assert "SkillA" in str(exc_info.value) or "SkillB" in str(exc_info.value)


@pytest.mark.asyncio
async def test_from_manifest_pipeline_execution_and_skip_disabled():
    """Steps 16, 20, 22: from_manifest builds and runs topological DAG, skipping disabled skills."""
    manifest_dict = {
        "skills": [
            {
                "name": "StepC",
                "class": "tests.unit.test_manifest_pipeline.DummyStepSkill",
                "depends_on": ["StepB"],
                "runs_after": ["StepB"],
                "runs_before": [],
                "config": {"enabled": True},
            },
            {
                "name": "StepA",
                "class": "tests.unit.test_manifest_pipeline.DummyStepSkill",
                "depends_on": [],
                "runs_after": [],
                "runs_before": ["StepB"],
                "config": {"enabled": True},
            },
            {
                "name": "StepB",
                "class": "tests.unit.test_manifest_pipeline.DummyStepSkill",
                "depends_on": ["StepA"],
                "runs_after": ["StepA"],
                "runs_before": ["StepC"],
                "config": {"enabled": True},
            },
            {
                "name": "DisabledSkill",
                "class": "tests.unit.test_manifest_pipeline.DummyStepSkill",
                "depends_on": [],
                "runs_after": [],
                "runs_before": [],
                "config": {"enabled": False},
            },
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yaml.safe_dump(manifest_dict, f)
        temp_path = f.name

    try:
        orch = Orchestrator.from_manifest(temp_path)
        # DisabledSkill must be excluded
        assert "DisabledSkill" not in orch._ordered_skill_names
        # Order must be StepA -> StepB -> StepC
        assert orch._ordered_skill_names == ["StepA", "StepB", "StepC"]

        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1)
        final_ctx = await orch.run(ctx)

        assert final_ctx.artifacts.get("execution_order") == ["StepA", "StepB", "StepC"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_production_manifest_order_and_plugins():
    """Step 23: Production manifest.yaml resolves correct topological order including plugins."""
    manifest_path = "src/agents/skills/manifest.yaml"
    assert os.path.exists(manifest_path)

    orch = Orchestrator.from_manifest(manifest_path)
    order = orch._ordered_skill_names

    # HistoricalAccuracyChecker must run before WritingSkill
    assert order.index("HistoricalAccuracyChecker") < order.index("WritingSkill")
    # WritingSkill must run before AuditSkill
    assert order.index("WritingSkill") < order.index("AuditSkill")
    # CulturalComplianceChecker must run after AuditSkill
    assert order.index("CulturalComplianceChecker") > order.index("AuditSkill")
