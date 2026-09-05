# tests/unit/test_skill_base.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult


class DummySkill(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={})


def test_skill_agent_abstract():
    """SkillAgent は抽象クラスであり、execute を実装しないとインスタンス化できない"""
    with pytest.raises(TypeError):
        SkillAgent()


def test_dummy_skill_instantiation():
    skill = DummySkill()
    assert skill.version == "1.0"
    assert hasattr(skill, '_safe_get_dict')
    assert hasattr(skill, '_safe_get_list')
    assert hasattr(skill, '_get_book_branch')


def test_discover_skills():
    skills = SkillAgent.discover_skills('src.agents.skills')
    # 少なくとも PlanningSkill などが見つかるはず
    skill_names = {s.__name__ for s in skills}
    assert 'PlanningSkill' in skill_names
    assert 'BibleSkill' in skill_names


def test_load_manifest():
    manifest = SkillAgent.load_manifest('src/agents/skills/manifest.yaml')
    assert isinstance(manifest, list)
    assert len(manifest) == 10
    names = {m['name'] for m in manifest}
    assert 'PlanningSkill' in names
    assert 'BibleSkill' in names
    assert 'EnrichmentSkill' in names


def test_skill_cache():
    # 2回呼び出しても同じリストが返ること（キャッシュ機能）
    skills1 = SkillAgent.discover_skills('src.agents.skills')
    skills2 = SkillAgent.discover_skills('src.agents.skills')
    assert skills1 is skills2