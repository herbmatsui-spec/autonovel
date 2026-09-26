import logging
from dataclasses import dataclass, field
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
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.model_selector import _type_value
from src.services.illustration.unified_generator import UnifiedIllustrationGenerator

logger = logging.getLogger(__name__)


class IllustrationAgent(SkillAgent):
    """イラスト作成サブエージェント（表紙 / 挿絵 / 立ち絵 / 6コマ / 24コマ）。

    生成は統合エンジン `UnifiedIllustrationGenerator` へ委譲する（生成モデルは
    `config/image_models.py` のカタログで一元管理、既定は NanoBanana2Lite）。
    `image_service` が渡された場合は後方互換のため Legacy Imagen 経路を使う。

    request は src / autonovel.src いずれの経路で生成された IllustrationRequest
    でも受け付けられるよう、isinstance に依存せず属性で判定する。
    """

    AGENT_NAME = "illustration"
    DISPLAY_NAME = "イラスト作成サブエージェント"

    def __init__(
        self,
        image_service: Any = None,
        config: UnifiedIllustrationConfig | None = None,
        generator: UnifiedIllustrationGenerator | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.image_service = image_service
        self.config = config or UnifiedIllustrationConfig()
        self.generator = generator or UnifiedIllustrationGenerator(
            config=self.config,
            llm=self.llm,
            image_service=image_service,
        )
        # 旧サービス群は後方互換のため遅延初期化（image_service 無しでも起動できる）
        self._cover_generator: CoverGenerator | None = None
        self._character_illustrator: CharacterIllustrator | None = None
        self._scene_illustrator: SceneIllustrator | None = None
        self._scene_service: SceneIllustrationService | None = None
        self._yonkoma_illustrator: YonkomaIllustrator | None = None

    # ---- 遅延プロパティ（旧サービス群） ----

    @property
    def cover_generator(self) -> CoverGenerator | None:
        if self._cover_generator is None and self.image_service is not None:
            self._cover_generator = CoverGenerator(self.image_service)
        return self._cover_generator

    @property
    def character_illustrator(self) -> CharacterIllustrator | None:
        if self._character_illustrator is None and self.image_service is not None:
            self._character_illustrator = CharacterIllustrator(self.image_service)
        return self._character_illustrator

    @property
    def scene_illustrator(self) -> SceneIllustrator | None:
        if self._scene_illustrator is None and self.image_service is not None:
            self._scene_illustrator = SceneIllustrator(self.image_service)
        return self._scene_illustrator

    @property
    def scene_service(self) -> SceneIllustrationService | None:
        if self._scene_service is None and self.image_service is not None:
            self._scene_service = SceneIllustrationService(self.image_service, llm=self.llm)
        return self._scene_service

    @property
    def yonkoma_illustrator(self) -> YonkomaIllustrator | None:
        if self._yonkoma_illustrator is None and self.image_service is not None:
            self._yonkoma_illustrator = YonkomaIllustrator(self.image_service)
        return self._yonkoma_illustrator

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

        # 再生成フォーカス取得（WritingService からの指示：visual_textual_synergy のみ対応）
        regeneration_focus = ctx.artifacts.get("regeneration_focus", [])
        regeneration_action = ctx.artifacts.get("regeneration_action")

        if "visual_textual_synergy" in regeneration_focus:
            ctx.artifacts["illustration_regeneration"] = True
            if regeneration_action:
                ctx.artifacts["illustration_focus"] = regeneration_action.illustration_focus
            logger.info("IllustrationAgent: 再生成モード - focus=visual_textual_synergy")

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
        """エージェントのメイン実行ロジック（画像生成）。

        kwargs:
            - request: IllustrationRequest
        """
        return await self.generate_prompt_only(**kwargs)

    async def generate_prompt_only(self, **kwargs) -> dict[str, Any]:
        """プロンプトを組み立て、統一エンジンで画像を生成して結果を返す。

        戻り値の形状 `{"status", "result", "prompt"}` は後方互換のため維持する。
        画像生成が失敗しても `{"status": "error", "message": ...}` を返し、
        呼び出し側（Orchestrator）を止めない。

        kwargs:
            - request: IllustrationRequest
        """
        try:
            request = self._coerce_request(kwargs.get("request"))

            result = await self.generator.generate(request)
            illustration_id = await self._persist(request, result)
            result.illustration_id = illustration_id
            return {"status": "success", "result": result, "prompt": result.prompt}
        except Exception as e:  # noqa: BLE001
            logger.error(f"IllustrationAgent generation error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def build_prompt_for(self, request) -> str:
        """種別プロンプトだけを構築する（生成なし）。"""
        request = self._coerce_request(request)
        strategy = self.generator.get_strategy(request)
        async_builder = getattr(strategy, "build_prompt_async", None)
        if callable(async_builder):
            return await async_builder(request)
        return strategy.build_prompt(request)

    async def _generate_cover(self, request: IllustrationRequest) -> IllustrationResult:
        """旧 API 互換。旧 CoverGenerator があればそれを、無ければ統一エンジンを使う。"""
        if self.cover_generator is not None:
            return await self.cover_generator.generate(request)
        return await self.generator.generate(request)

    async def _generate_character(self, request: IllustrationRequest) -> IllustrationResult:
        if self.character_illustrator is not None:
            return await self.character_illustrator.generate(request)
        return await self.generator.generate(request)

    async def _generate_episode(self, request: IllustrationRequest) -> IllustrationResult:
        """話数ごとの挿絵（単一）。統一エンジンへ委譲する。"""
        if self.scene_illustrator is not None and getattr(request, "scene_text", None):
            return await self.scene_illustrator.generate_for_scene(request.scene_text, request)
        return await self.generator.generate(request)

    # ---- 旧 *_prompt メソッド（後方互換・戦略へ委譲） ----

    async def _build_with_strategy(self, request: IllustrationRequest, illo_type) -> str:
        """指定種別の戦略でプロンプトを構築する。"""
        coerced = self._coerce_request(request)
        if getattr(coerced, "illustration_type", None) != illo_type:
            coerced = IllustrationRequest(
                book_id=coerced.book_id,
                illustration_type=illo_type,
                episode_number=coerced.episode_number,
                character_id=coerced.character_id,
                scene_text=coerced.scene_text,
                book_context=coerced.book_context,
                model=coerced.model,
                safety_level=coerced.safety_level,
                aspect_ratio=coerced.aspect_ratio,
                prompt_override=coerced.prompt_override,
                panels=coerced.panels,
            )
        strategy = self.generator.get_strategy(coerced)
        async_builder = getattr(strategy, "build_prompt_async", None)
        if callable(async_builder):
            return await async_builder(coerced)
        return strategy.build_prompt(coerced)

    async def _build_cover_prompt(self, request: IllustrationRequest) -> str:
        """表紙用プロンプト（`CoverStrategy` へ委譲）。"""
        return await self._build_with_strategy(request, IllustrationType.COVER)

    async def _build_character_prompt(self, request: IllustrationRequest) -> str:
        """キャラクター用プロンプト（`CharacterStrategy` へ委譲）。"""
        return await self._build_with_strategy(request, IllustrationType.CHARACTER)

    async def _build_episode_prompt(self, request: IllustrationRequest) -> str:
        """エピソード用プロンプト（`EpisodeStrategy` へ委譲）。"""
        return await self._build_with_strategy(request, IllustrationType.EPISODE)

    def _extract_scene_details(self, scene_text: str) -> tuple[str, str, str, str]:
        """
        シーンテキストから場所、時間帯、キャラクター詳細、アクションを抽出する。
        将来的にはNLPエンティティ抽出に置き換えることができる。
        """
        if not scene_text:
            return "", "", "", ""

        # 簡易的なキーワードベース抽出（実際の実装ではより高度なNLPを使用）
        scene_lower = scene_text.lower()

        # 場所キーワード
        locations = {
            "city": ["都市", "街", "町", "downtown", "street", "avenue", "city"],
            "forest": ["森", "林", "woods", "forest", "jungle"],
            "school": ["学校", "教室", "school", "classroom", "campus"],
            "home": ["家", "住宅", "home", "house", "apartment", "apato"],
            "cafe": ["カフェ", "喫茶店", "cafe", "coffee", "restaurant", "レストラン"],
            "mountain": ["山", "峠", "mountain", "hill", "peak"],
            "ocean": ["海", "浜", "beach", "ocean", "sea", "shore"],
        }

        location = ""
        for loc, keywords in locations.items():
            if any(keyword in scene_lower for keyword in keywords):
                location = loc
                break

        # 時間帯キーワード
        time_keywords = {
            "morning": ["朝", "午前", "morning", "dawn", "sunrise"],
            "afternoon": ["昼", "午後", "afternoon", "noon"],
            "evening": ["夕方", "夕暮れ", "evening", "dusk", "sunset"],
            "night": ["夜", "深夜", "night", "midnight", "moonlight", "starlight"],
            "golden_hour": ["魔法の時間", "golden hour", "twilight"],
        }

        time_of_day = ""
        for time, keywords in time_keywords.items():
            if any(keyword in scene_lower for keyword in keywords):
                time_of_day = time
                break

        # キャラクター表情キーワード
        expression_keywords = {
            "happy": ["笑顔", "嬉し", "楽し", "happy", "smile", "grin"],
            "sad": ["悲し", "泣", "sad", "tears", "crying", "frown"],
            "angry": ["怒り", "激怒", "angry", "furious", "rage"],
            "surprised": ["驚き", "びっくり", "surprised", "shocked", "amazed"],
            "determined": ["決意", "決闘", "determined", "resolved", "focused"],
            "calm": ["静か", "穏やか", "calm", "peaceful", "serene"],
        }

        character_details = ""
        for expr, keywords in expression_keywords.items():
            if any(keyword in scene_lower for keyword in keywords):
                character_details = expr
                break

        # アクションキーワード
        action_keywords = {
            "running": ["走る", "sprint", "run", "dash", "駆け"],
            "fighting": ["戦う", "闘う", "fight", "battle", "combat", "攻撃"],
            "talking": ["話す", "話し", "talk", "speak", "conversation", "会話"],
            "thinking": ["考える", "思う", "think", "ponder", "contemplate", "悩む"],
            "standing": ["立つ", "stand", "pose", "姿勢"],
            "sitting": ["座る", "sit", "座席"],
        }

        action = ""
        for act, keywords in action_keywords.items():
            if any(keyword in scene_lower for keyword in keywords):
                action = act
                break

        return location, time_of_day, character_details, action

    async def _build_yonkoma_prompt(self, request: IllustrationRequest) -> str:
        """6コマ要約漫画用プロンプト（`Yonkoma6Strategy` へ委譲）。"""
        return await self._build_with_strategy(request, IllustrationType.YONKOMA)

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

        if self.yonkoma_illustrator is not None:
            return await self.yonkoma_illustrator.generate(
                episode_text=episode_text,
                request=request,
                panels=panels,
                summaries=summaries,
            )

        # 旧 ImageService が無い場合は統一エンジンへ渡す
        yonkoma_request = IllustrationRequest(
            book_id=request.book_id,
            illustration_type=IllustrationType.YONKOMA,
            episode_number=request.episode_number,
            character_id=request.character_id,
            scene_text=episode_text,
            book_context=request.book_context,
            model=request.model,
            safety_level=request.safety_level,
            aspect_ratio=request.aspect_ratio,
            prompt_override=request.prompt_override,
            panels=panels,
        )
        result = await self.generator.generate(yonkoma_request)
        result.illustration_id = await self._persist(yonkoma_request, result)
        return result

    async def generate_manga_24panel(
        self,
        episode_text: str,
        request: IllustrationRequest,
        panels: int = 24,
    ) -> IllustrationResult:
        """本文から 24 コマ（4x6）の漫画シートを 1 枚生成する。"""
        from src.services.illustration.strategies.manga24 import TOTAL_PANELS

        manga_request = IllustrationRequest(
            book_id=request.book_id,
            illustration_type=IllustrationType.MANGA_24PANEL,
            episode_number=request.episode_number,
            character_id=request.character_id,
            scene_text=episode_text,
            book_context=request.book_context,
            model=request.model,
            safety_level=request.safety_level,
            aspect_ratio=request.aspect_ratio or "2:3",
            prompt_override=request.prompt_override,
            panels=min(max(1, panels), TOTAL_PANELS),
        )
        result = await self.generator.generate(manga_request)
        result.illustration_id = await self._persist(manga_request, result)
        return result

    async def generate_episode_scenes(
        self, request: IllustrationRequest
    ) -> list[IllustrationResult]:
        """本文から複数シーンを抽出し、各シーンの挿絵を生成して返す（シーン抽出機能）。"""
        if self.scene_service is not None:
            results = await self.scene_service.generate(request)
        else:
            from src.services.illustration.scene_service import SceneExtractor

            scenes = SceneExtractor().extract_scenes(request.scene_text or "", max_scenes=3)
            results = []
            for scene in scenes:
                scene_request = IllustrationRequest(
                    book_id=request.book_id,
                    illustration_type=IllustrationType.EPISODE,
                    episode_number=request.episode_number,
                    scene_text=scene,
                    book_context=request.book_context,
                    model=request.model,
                    safety_level=request.safety_level,
                    aspect_ratio=request.aspect_ratio,
                )
                results.append(await self.generator.generate(scene_request))
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
        request = self._coerce_request(request)

        # 强化ロジックは戦略側に集約（`PromptStrategy.regenerate_prompt`）
        strategy = self.generator.get_strategy(request)
        action = _RegenerationAction(params=params, focus=focus)
        result = strategy.regenerate_prompt(request, action)
        result["focus"] = focus
        return result


@dataclass
class _RegenerationAction:
    """`PromptStrategy.regenerate_prompt` へ渡す軽量アクション（dict 互換）。"""

    params: dict[str, Any] = field(default_factory=dict)
    focus: str = "visual_textual_synergy"
