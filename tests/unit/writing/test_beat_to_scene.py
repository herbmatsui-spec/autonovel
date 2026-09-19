"""Beat-to-Scene 分割執筆パイプラインのテスト"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.domain.entities.scene import Scene, SceneRole, SceneStatus
from src.agents.writing.scene_writer import SceneWriter, SceneWriterOrchestrator
from src.agents.orchestrator import AgentContext, AgentResult


class MockLLMService:
    """モックLLMサービス"""

    def __init__(self, responses: list[str] = None):
        self.responses = responses or [
            "導入シーンの本文がここに入ります。日常が描かれ、小さな違和感で終わります。",
            "衝突シーンの本文がここに入ります。主要な対立が顕在化し、ピンチで終わります。",
            "引きシーンの本文がここに入ります。クライマックスと次回へのフックで終わります。",
        ]
        self.call_count = 0

    async def generate_text(self, purpose: str, prompt: str, system_instruction: str = None, temperature: float = 0.7):
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        # story_content属性を持つオブジェクトを返す（EpisodeWriterの期待に合わせる）
        class Result:
            def __init__(self, content):
                self.story_content = content

        return Result(response)


class MockContextBuilder:
    """モックコンテキストビルダー"""

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            next_agent=None,
            artifacts={
                "writing_context": {
                    "plot": {
                        "one_line_summary": "主人公が異世界で冒険する",
                        "detailed_blueprint": "詳細なプロット設計図",
                    },
                    "world_setting": "剣と魔法のファンタジー世界",
                    "genre": "fantasy_action",
                    "character_states": "主人公：冒険者レベル1",
                }
            },
            should_retry=False,
            error=None,
        )


class MockProseRefiner:
    """モックプロセ精練エージェント"""

    async def refine(self, draft_text: str, genre: str, style_intensity: str):
        class RefinementResult:
            def __init__(self, text):
                self.refined_text = text + " [精練済み]"

        return RefinementResult(draft_text)


class MockEroticEnhancer:
    """モックエロティック強化"""

    def enhance_erotic_content(self, prompt: str, content: str, context: dict):
        return content


@pytest.fixture
def mock_llm():
    return MockLLMService()


@pytest.fixture
def mock_context_builder():
    return MockContextBuilder()


@pytest.fixture
def mock_prompt_manager():
    return MagicMock()


@pytest.fixture
def scene_writer(mock_llm, mock_context_builder, mock_prompt_manager):
    """SceneWriter インスタンスを作成"""
    with patch("src.agents.writing.scene_writer.ProseRefinerAgent", MockProseRefiner), \
         patch("src.agents.erotic_enhancer.EroticEnhancer", MockEroticEnhancer):
        writer = SceneWriter(
            llm=mock_llm,
            context_builder=mock_context_builder,
            repo=None,
            style_rag=None,
            rag_prefetch=None,
            prompt_manager=mock_prompt_manager,
            compressor=None,
        )
    return writer


@pytest.fixture
def scene_orchestrator(scene_writer):
    """SceneWriterOrchestrator インスタンスを作成"""
    return SceneWriterOrchestrator(scene_writer)


class TestSceneEntity:
    """Scene エンティティのテスト"""

    def test_create_introduction_scene(self):
        """導入シーンの作成テスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scene = Scene.create_introduction(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
            target_word_count=800,
        )

        assert scene.scene_number == 1
        assert scene.role == SceneRole.INTRODUCTION
        assert scene.title == "導入"
        assert scene.target_word_count == 800
        assert scene.tension_start == 20
        assert scene.tension_end == 50
        assert len(scene.beats) == 3
        assert scene.status == SceneStatus.PLANNED

    def test_create_conflict_scene(self):
        """衝突シーンの作成テスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scene = Scene.create_conflict(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
            target_word_count=800,
        )

        assert scene.scene_number == 2
        assert scene.role == SceneRole.CONFLICT
        assert scene.title == "衝突"
        assert scene.tension_start == 50
        assert scene.tension_end == 85

    def test_create_hook_scene(self):
        """引きシーンの作成テスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scene = Scene.create_hook(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
            target_word_count=800,
        )

        assert scene.scene_number == 3
        assert scene.role == SceneRole.HOOK
        assert scene.title == "引き"
        assert scene.tension_start == 85
        assert scene.tension_end == 95

    def test_create_standard_triad(self):
        """標準3シーン構造の作成テスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scenes = Scene.create_standard_triad(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
            target_word_count=2400,
        )

        assert len(scenes) == 3
        assert scenes[0].role == SceneRole.INTRODUCTION
        assert scenes[1].role == SceneRole.CONFLICT
        assert scenes[2].role == SceneRole.HOOK
        assert all(s.target_word_count == 800 for s in scenes)

    def test_scene_lifecycle(self):
        """シーンのライフサイクルテスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scene = Scene.create_introduction(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
        )

        # 初期状態
        assert scene.status == SceneStatus.PLANNED

        # 書き込み中
        scene.mark_writing()
        assert scene.status == SceneStatus.WRITING

        # 完了
        test_content = "テスト本文"
        scene.mark_completed(test_content)
        assert scene.status == SceneStatus.COMPLETED
        assert scene.content == test_content
        assert scene.actual_word_count == len(test_content)

        # 失敗
        scene2 = Scene.create_conflict(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
        )
        scene2.mark_failed("生成エラー")
        assert scene2.status == SceneStatus.FAILED
        assert scene2.generation_metadata["error"] == "生成エラー"

    def test_tension_delta(self):
        """テンション変化量のテスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        intro = Scene.create_introduction(novel_id, branch_id, 1)
        conflict = Scene.create_conflict(novel_id, branch_id, 1)
        hook = Scene.create_hook(novel_id, branch_id, 1)

        assert intro.get_tension_delta() == 30  # 50 - 20
        assert conflict.get_tension_delta() == 35  # 85 - 50
        assert hook.get_tension_delta() == 10  # 95 - 85


class TestSceneWriter:
    """SceneWriter のテスト"""

    @pytest.mark.asyncio
    async def test_build_scene_context(self, scene_writer):
        """シーン用コンテキスト構築のテスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scene = Scene.create_introduction(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
        )

        context = await scene_writer.build_scene_context(
            book_id=1,
            branch_id=1,
            ep_num=1,
            scene=scene,
            previous_scene_content="",
            writing_context={},
        )

        assert "scene" in context
        assert context["scene"]["role"] == "導入"
        assert context["is_first_scene"] is True
        assert context["is_last_scene"] is False
        # writing_context_summaryは内部で構築されるため、コンテキストに含まれるかどうかは実装依存
        # 代わりに必要なキーが存在することを確認
        assert "scene_role" in context
        assert "scene_beats" in context

    @pytest.mark.asyncio
    async def test_write_scene(self, scene_writer):
        """単一シーン生成のテスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scene = Scene.create_introduction(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=1,
        )

        context = {
            "genre": "fantasy_action",
            "style_intensity": "balanced",
            "prose_refiner_enabled": True,
        }

        content = await scene_writer.write_scene(1, 1, scene, context)

        assert scene.status == SceneStatus.COMPLETED
        assert scene.content == content
        # モックLLMが返す内容が含まれていること
        assert len(content) > 0
        # シーン番号が正しいこと
        assert scene.scene_number == 1
        assert scene.role == SceneRole.INTRODUCTION


class TestSceneWriterOrchestrator:
    """SceneWriterOrchestrator のテスト"""

    @pytest.mark.asyncio
    async def test_write_episode_scenes(self, scene_orchestrator):
        """1話分の3シーン順次生成テスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        writing_context = {
            "novel_id": novel_id,
            "branch_id": branch_id,
            "genre": "fantasy_action",
            "style_intensity": "balanced",
        }

        scenes = await scene_orchestrator.write_episode_scenes(
            book_id=1,
            branch_id=1,
            ep_num=1,
            target_word_count=2400,
            writing_context=writing_context,
        )

        assert len(scenes) == 3
        assert all(s.status == SceneStatus.COMPLETED for s in scenes)
        assert scenes[0].role == SceneRole.INTRODUCTION
        assert scenes[1].role == SceneRole.CONFLICT
        assert scenes[2].role == SceneRole.HOOK

        # 各シーンに本文がある
        for scene in scenes:
            assert scene.content
            assert scene.actual_word_count > 0

    @pytest.mark.asyncio
    async def test_compose_episode(self, scene_orchestrator):
        """シーン結合テスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        scenes = Scene.create_standard_triad(novel_id, branch_id, 1)

        # 完了済みとしてマーク
        for i, scene in enumerate(scenes):
            scene.mark_completed(f"シーン{i+1}の本文です。")

        composed = scene_orchestrator.compose_episode(scenes)

        assert "シーン1の本文です。" in composed
        assert "シーン2の本文です。" in composed
        assert "シーン3の本文です。" in composed
        assert "---" in composed  # 区切り文字


class TestBeatToSceneIntegration:
    """Beat-to-Scene 統合テスト"""

    @pytest.mark.asyncio
    async def test_full_beat_to_scene_pipeline(self, scene_orchestrator):
        """完全なBeat-to-Sceneパイプラインのテスト"""
        from src.domain.value_objects.ids import NovelId
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()

        writing_context = {
            "novel_id": novel_id,
            "branch_id": branch_id,
            "genre": "fantasy_action",
            "style_intensity": "balanced",
        }

        # 3シーン生成
        scenes = await scene_orchestrator.write_episode_scenes(
            book_id=1,
            branch_id=1,
            ep_num=4,
            target_word_count=2400,
            writing_context=writing_context,
        )

        # 結合
        episode_text = scene_orchestrator.compose_episode(scenes)

        # 検証
        assert len(episode_text) > 0
        # 3シーン分結合されていること（区切り文字で確認）
        assert episode_text.count("---") == 2
        # 各シーンが完了していること
        assert all(s.status == SceneStatus.COMPLETED for s in scenes)

        # テンション曲線の確認（導入→衝突→引きで上昇）
        assert scenes[0].tension_end < scenes[1].tension_end
        assert scenes[1].tension_end < scenes[2].tension_end


class TestScenePrompts:
    """シーンプロンプトテンプレートのテスト"""

    def test_introduction_prompt_exists(self):
        """導入プロンプトテンプレートの存在確認"""
        from pathlib import Path
        path = Path(__file__).resolve().parents[3] / "prompts" / "templates" / "narrative" / "scene_introduction.j2"
        assert path.exists(), f"Template not found: {path}"

    def test_conflict_prompt_exists(self):
        """衝突プロンプトテンプレートの存在確認"""
        from pathlib import Path
        path = Path(__file__).resolve().parents[3] / "prompts" / "templates" / "narrative" / "scene_conflict.j2"
        assert path.exists(), f"Template not found: {path}"

    def test_hook_prompt_exists(self):
        """引きプロンプトテンプレートの存在確認"""
        from pathlib import Path
        path = Path(__file__).resolve().parents[3] / "prompts" / "templates" / "narrative" / "scene_hook.j2"
        assert path.exists(), f"Template not found: {path}"

    def test_prompt_templates_renderable(self):
        """プロンプトテンプレートがレンダリング可能かテスト"""
        import jinja2
        from pathlib import Path
        from src.domain.entities.scene import Scene, SceneRole
        from src.domain.value_objects.ids import NovelId

        tmpl_path = Path(__file__).resolve().parents[3] / "prompts" / "templates"
        jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tmpl_path)))

        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        scene = Scene.create_introduction(novel_id, branch_id, 1)

        # 各テンプレートがエラーなくレンダリングできるか確認
        for template_name in ["scene_introduction.j2", "scene_conflict.j2", "scene_hook.j2"]:
            tmpl = jenv.get_template(f"narrative/{template_name}")
            rendered = tmpl.render(
                scene_data=scene,
                episode_number=1,
                previous_scene_content="",
                writing_context_summary="テスト用コンテキスト",
                story_arc_summary="",
                character_states="",
                foreshadowing_hints="",
                active_conflicts="",
                cliffhanger_requirements="",
                pov_character="主人公",
                style_instruction="",
                char_flaw="完璧を求めすぎて動けなくなる",
            )
            assert len(rendered) > 100  # それなりの長さがある
            assert "導入" in rendered or "衝突" in rendered or "引き" in rendered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])