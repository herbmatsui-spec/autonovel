# tests/integration/test_regression_phase4.py
"""Phase 4 実装後のリグレッションテスト（既存パイプライン無影響確認）"""
import pytest
import os

# ENRICHMENT_ENABLED=false で既存テストが通ることを確認
os.environ["ENRICHMENT_ENABLED"] = "false"


class TestRegressionPhase4:
    """Phase 4 変更によるリグレッションなしを確認"""

    def test_import_orchestrator(self):
        """Orchestrator インポート"""
        from src.agents.orchestrator import Orchestrator, AgentName, AgentContext, AgentResult
        assert AgentName.PLANNING
        assert AgentName.ENRICHMENT  # 新規追加

    def test_import_all_agents(self):
        """全エージェントインポート（直接インポート）"""
        from src.agents import (
            PlanningAgent, PlotAgent, BibleAgent, ContextBuilderAgent,
            WritingAgent, EnrichmentAgent, AuditAgent, MarketingAgent,
        )
        from src.agents.illustration_agent import IllustrationAgent
        # すべてインポート成功

    def test_import_skills_v1(self):
        """v1 スキルインポート（直接インポート）"""
        from src.agents.skills.v1 import EnrichmentSkill
        from src.agents.skills.v1.planning_skill import PlanningSkill
        from src.agents.skills.v1.bible_skill import BibleSkill
        from src.agents.skills.v1.context_builder_skill import ContextBuilderSkill
        from src.agents.skills.v1.writing_skill import WritingSkill
        from src.agents.skills.v1.audit_skill import AuditSkill
        from src.agents.skills.v1.illustration_skill import IllustrationSkill
        from src.agents.skills.v1.marketing_copy import MarketingCopySkill
        # すべてインポート成功

    def test_import_skills_v2(self):
        """v2 スキルインポート（直接インポート・v2は *SkillAgent 命名）"""
        from src.agents.skills.v2 import EnrichmentSkill
        from src.agents.skills.v2.planning_skill import PlanningSkillAgent
        from src.agents.skills.v2.bible_skill import BibleSkillAgent
        from src.agents.skills.v2.context_builder_skill import ContextBuilderSkillAgent
        from src.agents.skills.v2.writing_skill import WritingSkillAgent
        from src.agents.skills.v2.audit_skill import AuditSkillAgent
        from src.agents.skills.v2.illustration_skill import IllustrationSkillAgent
        # v2には marketing_copy はない
        # すべてインポート成功

    def test_manifest_loads(self):
        """マニフェスト読み込み"""
        from src.agents.skill_base import SkillAgent
        manifest = SkillAgent.load_manifest('src/agents/skills/manifest.yaml')
        assert isinstance(manifest, list)
        names = {m['name'] for m in manifest}
        assert 'PlanningSkill' in names
        assert 'EnrichmentSkill' in names  # 新規追加
        assert 'AuditSkill' in names
        assert 'IllustrationSkill' in names

    def test_skill_discovery_v1(self):
        """v1 スキル検出"""
        from src.agents.skill_base import SkillAgent
        skills = SkillAgent.discover_skills('src.agents.skills.v1')
        skill_names = {s.__name__ for s in skills}
        assert 'EnrichmentSkill' in skill_names
        assert 'WritingSkill' in skill_names
        assert 'AuditSkill' in skill_names

    def test_skill_discovery_v2(self):
        """v2 スキル検出"""
        from src.agents.skill_base import SkillAgent
        skills = SkillAgent.discover_skills('src.agents.skills.v2')
        skill_names = {s.__name__ for s in skills}
        assert 'EnrichmentSkill' in skill_names

    def test_event_bus_constants(self):
        """EventBus 定数"""
        from src.agents.event_bus import (
            ENRICHMENT_STARTED, ENRICHMENT_STEP_COMPLETED,
            ENRICHMENT_COMPLETED, ENRICHMENT_ERROR,
        )
        assert ENRICHMENT_STARTED == "enrichment.started"
        assert ENRICHMENT_STEP_COMPLETED == "enrichment.step_completed"
        assert ENRICHMENT_COMPLETED == "enrichment.completed"
        assert ENRICHMENT_ERROR == "enrichment.error"

    def test_enrichment_config_loads(self):
        """エンリッチメント設定読み込み"""
        import yaml
        with open("config/enrichment.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "enrichment" in config
        assert config["enrichment"]["enabled"] is False  # デフォルトOFF

    @pytest.mark.asyncio
    async def test_orchestrator_with_enrichment_node(self):
        """Orchestrator に ENRICHMENT ノード追加可能"""
        from src.agents.orchestrator import Orchestrator, AgentName, AgentContext, AgentResult
        from src.agents.enrichment_agent import EnrichmentAgent
        
        agent = EnrichmentAgent()
        orch = Orchestrator(nodes={
            AgentName.ENRICHMENT: agent.run,
        })
        
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        # ノード存在確認
        assert AgentName.ENRICHMENT in orch.nodes

    def test_generation_tasks_imports(self):
        """generation_tasks インポート"""
        from src.backend.tasks import generation_tasks
        assert hasattr(generation_tasks, '_generate_orchestrated')
        assert hasattr(generation_tasks, 'generate_chapter_orchestrated_task')

    def test_enrichment_prompts_exist(self):
        """プロンプトファイル存在"""
        from prompts.enrichment import (
            trivia_insertion, citation_attachment, sensory_expansion, multimedia_scenarios
        )
        assert hasattr(trivia_insertion, 'TRIVIA_INSERTION_PROMPT')
        assert hasattr(citation_attachment, 'CITATION_ATTACHMENT_PROMPT')
        assert hasattr(sensory_expansion, 'SENSORY_EXPANSION_PROMPT')
        assert hasattr(multimedia_scenarios, 'MULTIMEDIA_SCENARIO_PROMPT')

    def test_enrichment_templates_exist(self):
        """テンプレートファイル存在"""
        from pathlib import Path
        template_dir = Path("prompts/enrichment/templates")
        assert (template_dir / "manga_script.j2").exists()
        assert (template_dir / "radio_drama.j2").exists()
        assert (template_dir / "anime_storyboard.j2").exists()
        assert (template_dir / "live_action_shots.j2").exists()

    def test_sensory_module_imports(self):
        """感覚モジュールインポート"""
        from src.agents.enrichment.sensory import (
            detect_abstract_emotions, generate_sensory_details,
            replace_with_sensory_expansion, expand_sensory_details_pipeline,
            EMOTION_TO_SENSORY_MAP, EmotionSpan,
        )
        # すべてインポート成功

    def test_multimedia_module_imports(self):
        """マルチメディアモジュールインポート"""
        from src.agents.enrichment.multimedia import (
            classify_scene_type, render_manga_script, render_radio_drama,
            render_anime_storyboard, render_live_action_shots, generate_scenarios,
            SceneSegment,
        )
        # すべてインポート成功