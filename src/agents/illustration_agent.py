import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
)
from src.services.illustration import (
    CharacterIllustrator,
    CoverGenerator,
    SceneIllustrationService,
    SceneIllustrator,
    YonkomaIllustrator,
)
from src.services.illustration.model_selector import _type_value, is_r15, resolve_request_model
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class IllustrationAgent(SkillAgent):
    """イラスト作成サブエージェント（表紙 / 挿絵 / キャラクター）。

    request は src / autonovel.src いずれの経路で生成された IllustrationRequest
    でも受け付けられるよう、isinstance に依存せず属性で判定する。
    現在はプロンプト生成のみ対応、画像生成は将来実装。
    """

    AGENT_NAME = "illustration"
    DISPLAY_NAME = "イラスト作成サブエージェント"

    def __init__(self, image_service: ImageService, **kwargs):
        super().__init__(**kwargs)
        self.image_service = image_service
        self.cover_generator = CoverGenerator(image_service)
        self.character_illustrator = CharacterIllustrator(image_service)
        self.scene_illustrator = SceneIllustrator(image_service)
        self.scene_service = SceneIllustrationService(image_service, llm=self.llm)
        self.yonkoma_illustrator = YonkomaIllustrator(image_service)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント。"""
        request = ctx.artifacts.get("request")
        if request is None:
            self.emit_event("illustration.error", {
                "error": "request is required in artifacts",
            })
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="request is required in artifacts",
            )
        result_dict = await self.generate_prompt_only(request=request)
        
        self.emit_event("illustration.completed", {
            "illustration_type": getattr(request, "illustration_type", None),
            "book_id": getattr(request, "book_id", None),
        })

        return AgentResult(
            next_agent=None,
            artifacts={"illustration_result": result_dict},
        )

    def _coerce_request(self, request):
        """dict なら IllustrationRequest に、オブジェクトならそのまま返す。"""
        if isinstance(request, dict):
            return IllustrationRequest(**request)
        if hasattr(request, "illustration_type") and hasattr(request, "book_id"):
            return request
        raise ValueError("Invalid or missing illustration request")

    async def run(self, **kwargs) -> dict[str, Any]:
        """エージェントのメイン実行ロジック (将来の画像生成用)。

        kwargs:
            - request: IllustrationRequest
        """
        # 現在は画像生成未実装。プロンプトのみ返す generate_prompt_only を使用
        return await self.generate_prompt_only(**kwargs)

    async def generate_prompt_only(self, **kwargs) -> dict[str, Any]:
        """プロンプトのみ生成するメソッド (画像生成は将来実装)。

        kwargs:
            - request: IllustrationRequest
        """
        try:
            request = self._coerce_request(kwargs.get("request"))
            kind = _type_value(request.illustration_type)

            if kind == IllustrationType.COVER.value:
                prompt = await self._build_cover_prompt(request)
            elif kind == IllustrationType.CHARACTER.value:
                prompt = await self._build_character_prompt(request)
            elif kind == IllustrationType.YONKOMA.value:
                prompt = await self._build_yonkoma_prompt(request)
            else:
                prompt = await self._build_episode_prompt(request)

            # 画像生成は行わず、プロンプトとメタデータのみ返す
            result = IllustrationResult(
                request=request,
                image_url="",  # 画像生成未実装のため空
                prompt=prompt,
                model_used=resolve_request_model(request),
                generation_time_ms=0,
            )

            illustration_id = await self._persist(request, result)
            result.illustration_id = illustration_id
            return {"status": "success", "result": result, "prompt": prompt}
        except Exception as e:  # noqa: BLE001
            logger.error(f"IllustrationAgent prompt generation error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _generate_cover(self, request: IllustrationRequest) -> IllustrationResult:
        return await self.cover_generator.generate(request)

    async def _generate_character(self, request: IllustrationRequest) -> IllustrationResult:
        return await self.character_illustrator.generate(request)

    async def _generate_episode(self, request: IllustrationRequest) -> IllustrationResult:
        """話数ごとの挿絵（単一）。scene_text があればそのシーンを描画。"""
        if getattr(request, "scene_text", None):
            return await self.scene_illustrator.generate_for_scene(request.scene_text, request)

        # scene_text がない場合は book_context から汎用エピソードプロンプトを構築
        ctx = request.book_context or {}
        title = ctx.get("title", "")
        genre = ctx.get("genre", "")
        concept = ctx.get("concept", "")
        parts = [
            f"Scene illustration for episode {getattr(request, 'episode_number', None)}.",
        ]
        if title:
            parts.append(f"Title: {title}.")
        if genre:
            parts.append(f"Genre: {genre}.")
        if concept:
            parts.append(f"Atmosphere: {concept}.")
        parts.append(
            "Detailed background, cinematic lighting, rich detail, no text or letters in image."
        )
        prompt = " ".join(parts)
        if is_r15(request.safety_level):
            prompt += " Tasteful R15 artistic representation, intimate but not explicit."

        import time

        start = time.time()
        image_url = await self.image_service.generate(
            prompt=prompt,
            model=resolve_request_model(request),
            aspect_ratio=request.aspect_ratio,
            safety_level=request.safety_level,
        )
        elapsed = int((time.time() - start) * 1000)
        return IllustrationResult(
            request=request,
            image_url=image_url,
            prompt=prompt,
            model_used=resolve_request_model(request),
            generation_time_ms=elapsed,
        )

    async def _build_cover_prompt(self, request: IllustrationRequest) -> str:
        """表紙用プロンプトを構築 (将来の実装で使用)"""
        ctx = request.book_context or {}
        title = ctx.get("title", "無題")
        genre = ctx.get("genre", "ファンタジー")
        concept = ctx.get("concept", "")

        parts = [
            f"Book cover illustration for '{title}'",
            f"Genre: {genre}",
        ]
        if concept:
            parts.append(f"Concept: {concept}")
        parts.append(
            "Detailed, cinematic lighting, rich detail, professional book cover art, no text or letters in image"
        )

        if is_r15(request.safety_level):
            parts.append("Tasteful R15 artistic representation, intimate but not explicit")

        return ", ".join(parts)

    async def _build_character_prompt(self, request: IllustrationRequest) -> str:
        """キャラクター用プロンプトを構築 (将来の実装で使用)"""
        ctx = request.book_context or {}
        character_name = ctx.get("character_name", "主人公")
        character_desc = ctx.get("character_description", "")
        genre = ctx.get("genre", "ファンタジー")

        parts = [
            f"Character illustration of {character_name}",
            f"Genre: {genre}",
        ]
        if character_desc:
            parts.append(f"Description: {character_desc}")
        parts.append(
            "Detailed character design, anime/manga style, clean lines, no text or letters in image"
        )

        if is_r15(request.safety_level):
            parts.append("Tasteful R15 artistic representation, intimate but not explicit")

        return ", ".join(parts)

    async def _build_episode_prompt(self, request: IllustrationRequest) -> str:
        """エピソード用プロンプトを構築 (将来の実装で使用)"""
        ctx = request.book_context or {}
        title = ctx.get("title", "無題")
        genre = ctx.get("genre", "ファンタジー")
        episode_num = getattr(request, "episode_number", None)

        parts = [
            f"Scene illustration for episode {episode_num} of '{title}'",
            f"Genre: {genre}",
        ]
        parts.append(
            "Detailed background, cinematic lighting, rich detail, manga/anime style, no text or letters in image"
        )

        if is_r15(request.safety_level):
            parts.append("Tasteful R15 artistic representation, intimate but not explicit")

        return ", ".join(parts)

    async def _build_yonkoma_prompt(self, request: IllustrationRequest) -> str:
        """6コマ要約漫画用プロンプトを構築 (画像生成はせず文章のみ返す)。"""
        from src.services.illustration.prompts import build_yonkoma_prompt

        text = (getattr(request, "scene_text", "") or "").strip()
        panels = getattr(request, "panels", 6) or 6
        ctx = request.book_context or {}

        if text:
            from src.services.illustration.scene_service import YonkomaPlanner

            planner = YonkomaPlanner()
            if self.llm is not None:
                try:
                    summaries = await planner.plan_with_llm(text, self.llm, panels=panels)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Yonkoma LLM planning failed in agent: %s", e)
                    summaries = planner.plan_heuristic(text, panels=panels)
            else:
                summaries = planner.plan_heuristic(text, panels=panels)
        else:
            # シーン要約が無い場合は 6 個のプレースホルダで埋める (オンのとき UI で空でもエラーにしない)
            summaries = ["(導入)", "(展開)", "(転換)", "(高潮)", "(余韻)", "(次回への引き)"]

        prompt = build_yonkoma_prompt(summaries, ctx, panels=panels)
        if is_r15(request.safety_level):
            from src.services.illustration.prompts import apply_yonkoma_safety_modifier

            prompt = apply_yonkoma_safety_modifier(prompt, request.safety_level)
        return prompt

    async def generate_episode_yonkoma(
        self,
        episode_text: str,
        request: IllustrationRequest,
        panels: int = 6,
    ) -> IllustrationResult:
        """本文から 6 コマ要約漫画を生成して 1 枚の画像を返す。"""
        from src.services.illustration.scene_service import YonkomaPlanner

        planner = YonkomaPlanner()
        if self.llm is not None:
            try:
                summaries = await planner.plan_with_llm(episode_text, self.llm, panels=panels)
            except Exception as e:  # noqa: BLE001
                logger.warning("Yonkoma LLM planning failed: %s", e)
                summaries = planner.plan_heuristic(episode_text, panels=panels)
        else:
            summaries = planner.plan_heuristic(episode_text, panels=panels)

        return await self.yonkoma_illustrator.generate(
            episode_text=episode_text,
            request=request,
            panels=panels,
            summaries=summaries,
        )

    async def generate_episode_scenes(
        self, request: IllustrationRequest
    ) -> list[IllustrationResult]:
        """本文から複数シーンを抽出し、各シーンの挿絵を生成して返す（シーン抽出機能）。"""
        results = await self.scene_service.generate(request)
        for r in results:
            r.illustration_id = await self._persist(request, r)
        return results

    async def _persist(self, request, result: IllustrationResult) -> int | None:
        """生成結果をDBに保存する（repo がなければスキップ）。"""
        if self.repo is None or not hasattr(self.repo, "create_illustration"):
            return None
        try:
            return await self.repo.create_illustration(
                book_id=request.book_id,
                illustration_type=_type_value(request.illustration_type),
                image_url=result.image_url,
                prompt=result.prompt,
                episode_number=getattr(request, "episode_number", None),
                character_id=getattr(request, "character_id", None),
                model=result.model_used,
                safety_level=_type_value(request.safety_level),
                generation_time_ms=result.generation_time_ms,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to persist illustration: {e}")
            return None

    async def regenerate_prompts(
        self,
        request: IllustrationRequest,
        focus: str = "visual_textual_synergy",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """プロンプト再生成（視覚×テキスト相乗効果改善用）。
        
        Args:
            request: 元のリクエスト
            focus: 再生成フォーカス ("visual_textual_synergy" 等)
            params: 追加パラメータ
                - refocus_on_text_entities: 本文エンティティに焦点合わせ
                - match_emotional_tone: 感情トーン合わせ
        """
        params = params or {}
        ctx = request.book_context or {}
        
        # 本文からエンティティ抽出
        text_entities = []
        if params.get("refocus_on_text_entities"):
            scene_text = getattr(request, "scene_text", "") or ctx.get("scene_text", "")
            if scene_text:
                import re
                text_entities = list(set(re.findall(r'[一-龯ァ-ヴー]{2,}', scene_text)))[:20]
        
        # 感情トーン抽出
        emotional_tone = "neutral"
        if params.get("match_emotional_tone"):
            scene_text = getattr(request, "scene_text", "") or ctx.get("scene_text", "")
            if scene_text:
                positive = sum(scene_text.count(w) for w in ['喜', '笑', '幸', '楽', '愛', '希望', '輝', '明'])
                negative = sum(scene_text.count(w) for w in ['悲', '泣', '苦', '痛', '憎', '絶望', '暗', '闇', '恐'])
                if positive > negative:
                    emotional_tone = "positive"
                elif negative > positive:
                    emotional_tone = "negative"
        
        # 既存のプロンプトを取得して強化
        original_prompt = await self.generate_prompt_only(request=request)
        original = original_prompt.get("prompt", "")
        
        # 強化プロンプト構築
        enhancements = []
        if text_entities:
            enhancements.append(f"Key entities to include: {', '.join(text_entities[:10])}")
        if emotional_tone != "neutral":
            tone_desc = "bright and hopeful" if emotional_tone == "positive" else "dark and somber"
            enhancements.append(f"Emotional tone: {tone_desc}")
        
        enhanced_prompt = original
        if enhancements:
            enhanced_prompt = original + " | ENHANCEMENTS: " + "; ".join(enhancements)
        
        # 結果返却
        return {
            "status": "success",
            "original_prompt": original,
            "enhanced_prompt": enhanced_prompt,
            "enhancements_applied": enhancements,
            "focus": focus,
        }
