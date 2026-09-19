from typing import Any, List, Optional

from src.agents.base import BaseAgent
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.erotic_enhancer import EroticEnhancer
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.prompt_composer import PromptComposer
from src.agents.writing.prose_refiner_agent import ProseRefinerAgent
from src.agents.writing.scene_writer import SceneWriter, SceneWriterOrchestrator
from src.domain.entities.scene import SceneRole
from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository
from src.services.llm_service import LLMService
from src.services.rag.context_retriever import ForeshadowingEntity
from src.services.foreshadowing_service import ForeshadowingService
from src.services.prose.social_reaction_generator import SocialReactionGenerator
from src.models.writing_metadata import WritingMetadata
from src.services.prose.novel_output_splitter import NovelOutputSplitter
from prompts.manager import PromptManager
from src.pipeline.emotional_residue import EmotionalResidueExtractor
from src.stores.vector_store import RedisVectorStore
from src.pipeline.character_dict import load_character_dict


class EpisodeWriter(BaseAgent):
    def __init__(
        self,
        llm: LLMService,
        context_builder: ContextBuilderAgent,
        repo: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        context_retriever: Any = None,
        prompt_manager: PromptManager = None,
        compressor: Any = None,
        vector_store: Any = None,
        character_dict_path: str = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.context_builder = context_builder
        self.context_retriever = context_retriever
        self.prompt_manager = prompt_manager
        self.compressor = compressor
        self.vector_store = vector_store
        
        # 感情残基抽出器（遅延初期化）
        self._emotional_extractor: Optional[EmotionalResidueExtractor] = None
        self._character_dict_path = character_dict_path

        # Beat-to-Scene 分割執筆用のオーケストレーター（遅延初期化）
        self._scene_orchestrator: Optional[SceneWriterOrchestrator] = None
        self.last_metadata: Optional[WritingMetadata] = None
    
    def _get_emotional_extractor(self) -> Optional[EmotionalResidueExtractor]:
        """感情残基抽出器を遅延初期化して取得"""
        if self._emotional_extractor is None and self.vector_store:
            try:
                char_dict = load_character_dict(self._character_dict_path)
                self._emotional_extractor = EmotionalResidueExtractor(
                    vector_store=self.vector_store,
                    character_dict=char_dict,
                )
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"感情残基抽出器初期化失敗: {e}")
                return None
        return self._emotional_extractor

    def _get_scene_orchestrator(self) -> SceneWriterOrchestrator:
        """SceneWriterOrchestratorを遅延初期化して取得する。"""
        if self._scene_orchestrator is None:
            scene_writer = SceneWriter(
                llm=self.llm,
                context_builder=self.context_builder,
                repo=self.repo,
                style_rag=self.style_rag,
                rag_prefetch=self.rag_prefetch,
                prompt_manager=self.prompt_manager,
                compressor=self.compressor,
            )
            self._scene_orchestrator = SceneWriterOrchestrator(scene_writer)
        return self._scene_orchestrator

    async def write_beat_to_scene(
        self,
        book_id: int,
        ep_num: int,
        context: dict[str, Any],
        target_word_count: int = 2400,
        custom_beats: Optional[dict[SceneRole, List[str]]] = None,
    ) -> str:
        """
        Beat-to-Scene 分割執筆でエピソード本文を生成する。
        1話を3シーン（導入・衝突・引き）に分割し、順次生成して結合する。

        Args:
            book_id: 書籍ID
            ep_num: エピソード番号
            context: 執筆コンテキスト
            target_word_count: 目標文字数（3シーンで均等配分）
            custom_beats: カスタムビート（シーン役割ごとのビートリスト）

        Returns:
            生成された本文（3シーン結合済み）
        """
        orchestrator = self._get_scene_orchestrator()

        # 3シーン順次生成
        scenes = await orchestrator.write_episode_scenes(
            book_id=book_id,
            branch_id=context.get("branch_id", 1),
            ep_num=ep_num,
            target_word_count=target_word_count,
            writing_context=context,
            custom_beats=custom_beats,
        )

        # シーンを結合して1話の本文として返す
        composed_text = orchestrator.compose_episode(scenes)

        # エロティックコンテンツを強化（結合後の全文に対して）
        erotic_enhancer = EroticEnhancer(self)
        composed_text = erotic_enhancer.enhance_erotic_content("", composed_text, context)

        # プロセ精練（オプション）
        try:
            genre = context.get("genre", "fantasy_action")
            style_intensity = context.get("style_intensity", "balanced")
            prose_refiner_enabled = context.get("prose_refiner_enabled", True)
            if prose_refiner_enabled:
                refiner = ProseRefinerAgent()
                refinement_result = await refiner.refine(
                    draft_text=composed_text,
                    genre=genre,
                    style_intensity=style_intensity,
                )
                composed_text = refinement_result.refined_text
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"Ep.{ep_num}: プロセ精練失敗: {e}")

        # ダンジョン配信ジャンルの場合、配信コメントブロックを追加
        if genre in ["dungeon_stream", "streaming_fantasy", "modern_fantasy"]:
            try:
                social_generator = SocialReactionGenerator(self.llm)

                # クライマックス部分を抽出（最後のシーン=引きシーンを使用）
                hook_scene = next((s for s in scenes if s.role == SceneRole.HOOK), None)
                climax_text = hook_scene.content if hook_scene else composed_text[-500:]

                comments = await social_generator.generate_stream_comments(
                    highlight_description=climax_text,
                    count=20,
                )

                if comments:
                    comment_block = "\n\n【配信コメント】\n"
                    for comment in comments[:10]:
                        comment_block += f"{comment.user}: {comment.text}\n"

                    composed_text = composed_text + comment_block

                    if hasattr(self, "logger"):
                        self.logger.info(f"Ep.{ep_num}: 配信コメントブロックを追加 ({len(comments)}件生成)")
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"Ep.{ep_num}: 配信コメント生成でエラー: {e}")

        clean_text, self.last_metadata = NovelOutputSplitter.split_novel_output(composed_text)
        return clean_text

    def detect_resolved_foreshadowings(
        self, content: str, pending_list: List[ForeshadowingEntity]
    ) -> List[str]:
        """生成された本文中から解決された伏線を簡易検知する。

        Args:
            content: 生成されたエピソード本文
            pending_list: 現在未回収の伏線リスト

        Returns:
            解決されたと判断された伏線のIDリスト
        """
        resolved_ids = []
        if not content or not pending_list:
            return resolved_ids

        content_lower = content.lower()
        for fs in pending_list:
            # キーワードのいずれかが本文に含まれているかをチェック
            for keyword in fs.keywords:
                if keyword.lower() in content_lower:
                    resolved_ids.append(fs.foreshadow_id)
                    break  # 1つでもキーワードが見つかったらその伏線は解決とみなす
            # 解決描写の簡易チェック（例: 「解決した」「明らかになった」等）
            # ここではキーワードチェックのみとする
        return resolved_ids

    async def build_context(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: str | None = None,
    ) -> dict[str, Any]:
        """執筆に必要な完全なコンテキストを構築する。"""
        ctx = AgentContext(
            book_id=book_id,
            branch_id=branch_id,
            ep_num=ep_num,
            artifacts={
                "target_word_count": target_word_count,
                "style_tag": style_tag,
                "compressor": self.compressor,
            },
        )
        result = await self.context_builder.execute(ctx)
        return result.artifacts.get("writing_context", {})

    async def write(self, book_id: int, ep_num: int, context: dict[str, Any]) -> str:
        """
        エピソード本文を生成し、文字列で返す。
        :param book_id: 書籍ID
        :param ep_num: エピソード番号
        :param context: プロット情報、キャラ設定、世界設定などを含む辞書
        :return: 生成された本文（文字列）
        """
        # Beat-to-Scene 分割執筆が有効な場合はこちらを使用
        use_beat_to_scene = context.get("use_beat_to_scene", True)
        if use_beat_to_scene:
            target_word_count = context.get("target_word_count", 2400)
            custom_beats = context.get("custom_beats")
            return await self.write_beat_to_scene(
                book_id=book_id,
                ep_num=ep_num,
                context=context,
                target_word_count=target_word_count,
                custom_beats=custom_beats,
            )

        # 従来の一括生成（フォールバック/後方互換）
        # プロンプトを構築
        prompt_composer = PromptComposer(self)
        prompt = await prompt_composer.compose_writing_prompt(book_id, ep_num, context)

        # 初期結果を生成
        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
        )
        if hasattr(result, "story_content"):
            result = result.story_content

        # エロティックコンテンツを強化
        erotic_enhancer = EroticEnhancer(self)
        result = erotic_enhancer.enhance_erotic_content(prompt, result, context)

        # プロセ精練（オプション）
        try:
            # 設定からジャンルとスタイル強度を取得（デフォルト値を設定）
            genre = context.get("genre", "fantasy_action")
            style_intensity = context.get("style_intensity", "balanced")
            prose_refiner_enabled = context.get("prose_refiner_enabled", True)
            if prose_refiner_enabled:
                refiner = ProseRefinerAgent()
                refinement_result = await refiner.refine(
                    draft_text=result,
                    genre=genre,
                    style_intensity=style_intensity
                )
                result = refinement_result.refined_text
        except Exception:
            # プロセ精練に失敗しても、元のテキストを返す（フォールバック）
            pass

        # Step 12: ダンジョン配信ジャンル等の場合、戦闘クライマックス後に自動で配信コメントブロックを本文へ結合する
        if genre in ["dungeon_stream", "streaming_fantasy", "modern_fantasy"]:
            try:
                # 社会反応ジェネレーターを初期化
                social_generator = SocialReactionGenerator(self.llm)

                # クライマックス部分を抽出（本文の最後の20%をクライマックスとみなす）
                climax_start_index = len(result) * 4 // 5  # 80%地点から開始
                if climax_start_index < len(result):
                    climax_text = result[climax_start_index:]
                else:
                    climax_text = result[-100:] if len(result) > 100 else result  # フォールバック

                # 配信コメントを生成
                comments = await social_generator.generate_stream_comments(
                    highlight_description=climax_text,
                    count=20
                )

                # コメントブロックをフォーマット
                if comments:
                    comment_block = "\n\n【配信コメント】\n"
                    for comment in comments[:10]:  # 最大10件まで表示
                        comment_block += f"{comment.user}: {comment.text}\n"

                    # 本文の終わりにコメントブロックを追加
                    result = result + comment_block

                    if hasattr(self, "logger"):
                        self.logger.info(f"Ep.{ep_num}: 配信コメントブロックを追加 ({len(comments)}件生成)")
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"Ep.{ep_num}: 配信コメント生成でエラー: {e}")

        clean_result, self.last_metadata = NovelOutputSplitter.split_novel_output(str(result))
        return clean_result

    async def run(self, ctx: AgentContext) -> AgentResult:
        """エージェント固有のメインロジック。サブクラスで実装する。"""
        book_id = ctx.book_id
        ep_num = ctx.ep_num
        # The writing context should be in the artifacts from the context_builder_agent
        writing_context = ctx.artifacts.get("writing_context", {})
        # Generate the written text
        written_text = await self.write(book_id, ep_num, writing_context)
        writing_metadata = getattr(self, "last_metadata", None)

        # Step 8: 本文生成後に伏線自動回収を実行
        try:
            repo = ctx.artifacts.get("repo")
            session = ctx.artifacts.get("session") or getattr(repo, "session", None)
            if repo and session:
                foreshadowing_repo = DbForeshadowingRepository(session)
                foreshadowing_service = ForeshadowingService(foreshadowing_repo)
                resolved_titles = await foreshadowing_service.check_and_resolve(
                    book_id=book_id,
                    episode_num=ep_num,
                    draft_text=written_text,
                    writing_metadata=writing_metadata,
                )
                if resolved_titles:
                    if hasattr(self, "logger"):
                        self.logger.info(f"Ep.{ep_num}: 伏線自動回収 - {', '.join(resolved_titles)}")
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"Ep.{ep_num}: 伏線自動回収でエラー: {e}")

        # Return the result with the written text in artifacts
        # エピソード終了後に感情残基を抽出・永続化
        try:
            extractor = self._get_emotional_extractor()
            if extractor and written_text:
                extractor.extract_and_persist(f"ep{ep_num}", written_text)
                if hasattr(self, "logger"):
                    self.logger.info(f"Ep.{ep_num}: 感情残基抽出完了")
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"Ep.{ep_num}: 感情残基抽出でエラー: {e}")

        return AgentResult(
            next_agent=None,
            artifacts={
                "written_text": written_text,
                "writing_metadata": writing_metadata,
            },
            should_retry=False,
            error=None,
        )
