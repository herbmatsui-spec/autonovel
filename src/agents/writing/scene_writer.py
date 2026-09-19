"""SceneWriter - 個別シーン生成エージェント（Beat-to-Scene 分割執筆）"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.agents.base import BaseAgent
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.prompt_composer import PromptComposer
from src.agents.writing.prose_refiner_agent import ProseRefinerAgent
from src.domain.entities.scene import Scene, SceneRole
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class SceneWriter(BaseAgent):
    """個別シーン（導入・衝突・引き）を順次生成するライター。

    1話を3シーンに分割し、各シーンを独立したプロンプトで生成することで、
    「冗長な会話ループ」と「中身のない引き伸ばし」を物理的に防止する。
    """

    SCENE_PROMPT_TEMPLATES = {
        SceneRole.INTRODUCTION: "scene_introduction.j2",
        SceneRole.CONFLICT: "scene_conflict.j2",
        SceneRole.HOOK: "scene_hook.j2",
    }

    def __init__(
        self,
        llm: LLMService,
        context_builder: ContextBuilderAgent,
        repo: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        prompt_manager: Any = None,
        compressor: Any = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.context_builder = context_builder
        self.prompt_manager = prompt_manager
        self.compressor = compressor

    async def build_scene_context(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        scene: Scene,
        previous_scene_content: str = "",
        writing_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """シーン生成用のコンテキストを構築する。"""
        base_context = writing_context or {}

        # 前シーンの内容をコンテキストに含める（衝突・引きの場合）
        scene_context = {
            **base_context,
            "scene": scene.to_dict(),
            "previous_scene_content": previous_scene_content,
            "is_first_scene": scene.scene_number == 1,
            "is_last_scene": scene.scene_number == 3,
            "scene_role": scene.role.value,
            "scene_beats": scene.beats,
            "scene_tension_start": scene.tension_start,
            "scene_tension_end": scene.tension_end,
            "target_word_count": scene.target_word_count,
        }

        # 文脈構築エージェントで追加情報を取得
        ctx = AgentContext(
            book_id=book_id,
            branch_id=branch_id,
            ep_num=ep_num,
            artifacts={
                "target_word_count": scene.target_word_count,
                "scene_context": scene_context,
                "compressor": self.compressor,
            },
        )
        result = await self.context_builder.execute(ctx)
        writing_ctx = result.artifacts.get("writing_context", {})

        return {**scene_context, **writing_ctx}

    async def write_scene(
        self,
        book_id: int,
        ep_num: int,
        scene: Scene,
        context: dict[str, Any],
    ) -> str:
        """単一シーンを生成する。"""
        scene.mark_writing()

        # シーン用プロンプトを構築
        prompt_composer = PromptComposer(self)
        prompt = await prompt_composer.compose_scene_prompt(
            book_id, ep_num, scene, context
        )

        # LLMで生成
        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
        )
        if hasattr(result, "story_content"):
            content = result.story_content
        else:
            content = str(result)

        # プロセ精練（オプション）
        try:
            genre = context.get("genre", "fantasy_action")
            style_intensity = context.get("style_intensity", "balanced")
            prose_refiner_enabled = context.get("prose_refiner_enabled", True)
            if prose_refiner_enabled:
                refiner = ProseRefinerAgent()
                refinement_result = await refiner.refine(
                    draft_text=content,
                    genre=genre,
                    style_intensity=style_intensity,
                )
                content = refinement_result.refined_text
        except Exception as e:
            logger.warning(f"Scene {scene.scene_number} prose refinement failed: {e}")

        scene.mark_completed(content)
        return content

    async def run(self, ctx: AgentContext) -> AgentResult:
        """エージェントのメインエントリーポイント（単一シーン生成用）。"""
        book_id = ctx.book_id
        ep_num = ctx.ep_num
        scene = ctx.artifacts.get("scene")
        previous_scene_content = ctx.artifacts.get("previous_scene_content", "")
        writing_context = ctx.artifacts.get("writing_context", {})

        if not scene:
            return AgentResult(
                next_agent=None,
                artifacts={},
                should_retry=False,
                error="No scene provided in context",
            )

        try:
            # コンテキスト構築
            context = await self.build_scene_context(
                book_id, ctx.branch_id, ep_num, scene,
                previous_scene_content, writing_context
            )

            # シーン生成
            content = await self.write_scene(book_id, ep_num, scene, context)

            return AgentResult(
                next_agent=None,
                artifacts={
                    "scene": scene,
                    "scene_content": content,
                },
                should_retry=False,
                error=None,
            )
        except Exception as e:
            scene.mark_failed(str(e))
            logger.error(f"Scene {scene.scene_number} generation failed: {e}")
            return AgentResult(
                next_agent=None,
                artifacts={"scene": scene},
                should_retry=True,
                error=str(e),
            )


class SceneWriterOrchestrator:
    """3シーン（導入・衝突・引き）を順次生成するオーケストレーター。"""

    def __init__(self, scene_writer: SceneWriter):
        self.scene_writer = scene_writer

    async def write_episode_scenes(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        writing_context: dict[str, Any],
        custom_beats: Optional[dict[SceneRole, list[str]]] = None,
    ) -> list[Scene]:
        """1話分の3シーンを順次生成し、Sceneオブジェクトのリストを返す。"""
        # 3シーン構造を作成
        from src.domain.value_objects.ids import NovelId
        novel_id_any = writing_context.get("novel_id")
        branch_id_any = writing_context.get("branch_id")
        scene_novel_id: NovelId = novel_id_any if isinstance(novel_id_any, NovelId) else NovelId.generate()
        scene_branch_id: NovelId = branch_id_any if isinstance(branch_id_any, NovelId) else NovelId.generate()
        scenes = Scene.create_standard_triad(
            novel_id=scene_novel_id,
            branch_id=scene_branch_id,
            episode_number=ep_num,
            target_word_count=target_word_count,
            custom_beats=custom_beats,
        )

        previous_content = ""
        completed_scenes = []

        for scene in scenes:
            logger.info(
                f"Generating scene {scene.scene_number}/3 ({scene.role.value}) "
                f"for episode {ep_num}"
            )

            # エージェントコンテキスト作成
            agent_ctx = AgentContext(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=ep_num,
                artifacts={
                    "scene": scene,
                    "previous_scene_content": previous_content,
                    "writing_context": writing_context,
                },
            )

            # シーン生成実行
            result = await self.scene_writer.run(agent_ctx)

            if result.error:
                logger.error(f"Scene {scene.scene_number} failed: {result.error}")
                # 失敗しても次のシーンへ進む（部分的成果を残す）
                completed_scenes.append(scene)
                continue

            new_scene = result.artifacts.get("scene")
            if new_scene is not None:
                scene = new_scene
            scene_content = result.artifacts.get("scene_content", "")
            completed_scenes.append(scene)
            previous_content = scene_content

        return completed_scenes

    def compose_episode(self, scenes: list[Scene]) -> str:
        """完了したシーン群を1話の本文として結合する。"""
        parts = []
        for scene in scenes:
            if scene.status.value == "completed" and scene.content:
                # シーン見出しを追加（オプション）
                parts.append(scene.content)
            else:
                logger.warning(f"Scene {scene.scene_number} ({scene.role.value}) not completed, skipping")

        return "\n\n---\n\n".join(parts)


__all__ = [
    "SceneWriter",
    "SceneWriterOrchestrator",
]
