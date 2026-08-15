# agents/writing.py
import json
import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.agents.context_builder import ContextBuilder
from src.agents.episode_pipeline import EpisodePipeline
from src.core.interfaces import IPromptManager
from src.services.llm_service import LLMService

from .bible_extractor import BibleExtractor

# 新しいコンポーネントクラスをインポート（同じパッケージ内）
from .episode_writer import EpisodeWriter
from .rewrite_orchestrator import RewriteOrchestrator

logger = logging.getLogger(__name__)


class WritingAgent(BaseAgent):
    """執筆を担当するエージェント。
    プロンプトマネージャと LLM サービスを使用して、エピソード本文を生成する。
    これは分割後のファサードクラスであり、内部的には専門クラスに委譲する。
    """

    def __init__(
        self,
        repo: Any = None,
        llm: Optional[LLMService] = None,
        prompt_manager: Optional[IPromptManager] = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        plot_expander: Any = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.prompt_manager = prompt_manager
        self._plot_expander = plot_expander

        # 分割後のコンポーネントを初期化
        context_builder = ContextBuilder(self)
        self._episode_writer = EpisodeWriter(llm, context_builder)
        # TODO: 適切な auditor と spice_guard を注入する必要があります
        # 現在はプレースホルダーとして None を設定
        self._rewrite_orchestrator = RewriteOrchestrator(
            writer=self._episode_writer,
            auditor=None,  # TODO: 適切なauditorを注入
            spice_guard=None  # TODO: 適切なspice_guardを注入
        )
        self._bible_extractor = BibleExtractor(llm)

    # 元のメソッドをオーバーライドして、新しいコンポーネントに委譲する（後方互換性のため）
    async def _get_plot(self, book_id: int, branch_id: int, ep_num: int) -> Optional[Any]:
        """プロットをDBから取得する。"""
        if self.repo is None:
            return None
        try:
            return await self.repo.get_plot(book_id, ep_num, branch_id=branch_id)
        except Exception as e:
            logger.debug(f"Plot not found for book={book_id}, branch={branch_id}, ep={ep_num}: {e}")
            return None

    async def _get_book(self, book_id: int) -> Optional[Any]:
        """作品情報をDBから取得する。"""
        if self.repo is None:
            return None
        try:
            return await self.repo.get_book(book_id)
        except Exception as e:
            logger.debug(f"Book not found for book_id={book_id}: {e}")
            return None

    async def _get_chars(self, book_id: int) -> List[Any]:
        """作品に所属する全キャラクターを取得する。"""
        if self.repo is None:
            return []
        try:
            return await self.repo.get_all_characters(book_id)
        except Exception as e:
            logger.debug(f"Characters not found for book_id={book_id}: {e}")
            return []

    async def _get_prev_chapter(self, book_id: int, branch_id: int, ep_num: int) -> Optional[Any]:
        """前話の章データを取得する。"""
        if self.repo is None or ep_num <= 1:
            return None
        try:
            return await self.repo.get_chapter(branch_id, ep_num - 1)
        except Exception as e:
            logger.debug(
                f"Previous chapter not found for book={book_id}, branch={branch_id}, ep={ep_num}: {e}"
            )
            return None

    async def _get_active_chars(self, chars: List[Any], plot: Any) -> List[Any]:
        """プロットに登場するキャラクター名からアクティブなキャラクターを抽出する。"""
        if not plot or not chars:
            return chars
        try:
            plot_text = ""
            if hasattr(plot, "detailed_blueprint") and plot.detailed_blueprint:
                plot_text = plot.detailed_blueprint
            elif hasattr(plot, "summary") and plot.summary:
                plot_text = plot.summary
            if not plot_text:
                return chars
            active_names = set()
            for char in chars:
                name = getattr(char, "name", None)
                if name and name in plot_text:
                    active_names.add(name)
            if active_names:
                return [c for c in chars if getattr(c, "name", None) in active_names]
            return chars
        except Exception as e:
            logger.debug(f"Active char extraction failed: {e}")
            return chars

    def _build_char_static_ctx(self, chars: List[Any]) -> str:
        """キャラクターの不変属性を整形する。"""
        if not chars:
            return ""
        lines = []
        for char in chars:
            name = getattr(char, "name", "不明")
            role = getattr(char, "role", "")
            reg = char.to_safe_dict() if hasattr(char, "to_safe_dict") else {}
            surface = reg.get("surface_persona", "")
            personality = reg.get("personality", reg.get("inner_conflict", ""))
            parts = [f"- {name} ({role})"]
            if surface:
                parts.append(f"  表層: {surface}")
            if personality:
                parts.append(f"  内面: {personality}")
            lines.append("\n".join(parts))
        return "\n".join(lines)

    def _build_char_dynamic_ctx(self, chars: List[Any], prev_chapter: Optional[Any]) -> str:
        """キャラクターの動的状態を整形する。"""
        if not chars:
            return ""
        lines = []
        for char in chars:
            name = getattr(char, "name", "不明")
            reg = char.to_safe_dict() if hasattr(char, "to_safe_dict") else {}
            location = reg.get("location", "不明")
            inventory = reg.get("inventory", [])
            status = reg.get("status", "通常")
            parts = [f"- {name}: 場所={location}, 状態={status}"]
            if inventory:
                parts.append(f"  所持: {', '.join(inventory)}")
            lines.append("\n".join(parts))
        ctx = "\n".join(lines)
        if prev_chapter:
            ws = getattr(prev_chapter, "world_state", None)
            if ws:
                if isinstance(ws, str):
                    try:
                        ws = json.loads(ws)
                    except Exception:
                        ws = None
                if isinstance(ws, dict):
                    changes = ws.get("character_status_changes", [])
                    if changes:
                        ctx += "\n\n【前話でのステータス変更】\n"
                        ctx += "\n".join([f"- {c}" for c in changes[:10]])
        return ctx

    def _build_prev_ctx(
        self, prev_chapter: Optional[Any], book_id: int, branch_id: int, ep_num: int
    ) -> str:
        """前話までの文脈を整形する。"""
        if prev_chapter is None:
            return ""
        parts = []
        content = getattr(prev_chapter, "content", None)
        if content:
            parts.append(f"【前話本文(末尾500文字)】\n{content[-500:]}")
        summary = getattr(prev_chapter, "summary", None)
        if summary:
            parts.append(f"【前話あらすじ】\n{summary}")
        ai_insight = getattr(prev_chapter, "ai_insight", None)
        if ai_insight:
            parts.append(f"【前話の確定事実・伏線回収】\n{ai_insight}")
        if not parts:
            return ""
        return "\n\n".join(parts)

    def _build_dialogue_profiles(self, chars: List[Any]) -> Dict[str, str]:
        """各キャラクターの会話プロファイルを構築する。"""
        profiles = {}
        for char in chars:
            name = getattr(char, "name", None)
            if not name:
                continue
            reg = char.to_safe_dict() if hasattr(char, "to_safe_dict") else {}
            parts = []
            if reg.get("speech_pattern"):
                parts.append(f"話し方: {reg['speech_pattern']}")
            if reg.get("forbidden_words"):
                parts.append(f"禁止語: {', '.join(reg['forbidden_words'])}")
            if reg.get("catchphrase"):
                parts.append(f"口癖: {reg['catchphrase']}")
            profiles[name] = "; ".join(parts) if parts else name
        return profiles

    async def _ensure_plot_exists(self, book_id: int, branch_id: int, ep_num: int) -> Optional[Any]:
        """プロットが存在しない場合、生成を試みる。"""
        plot = await self._get_plot(book_id, branch_id, ep_num)
        if plot is None and self._plot_expander is not None:
            try:
                logger.info(f"Plot missing for Ep.{ep_num}, attempting on-demand generation...")
                arcs: List[Any] = []
                bible = await self._get_bible(book_id)
                if bible and hasattr(bible, "arcs"):
                    arcs = bible.arcs
                elif bible and isinstance(bible, dict):
                    arcs = bible.get("arcs", [])
                results = await self._plot_expander.expand_plots(
                    book_id=book_id,
                    target_ep_list=[ep_num],
                    arcs=arcs,
                    reporter=None,
                    force=False,
                    branch_id=branch_id,
                )
                if results:
                    plot = results[0]
                    logger.info(f"On-demand plot generated for Ep.{ep_num}")
            except Exception as e:
                logger.warning(f"On-demand plot generation failed for Ep.{ep_num}: {e}")
        return plot

    async def _get_bible(self, book_id: int) -> Optional[Any]:
        """最新のバイブルを取得する。"""
        if self.repo is None:
            return None
        try:
            return await self.repo.get_latest_bible(book_id)
        except Exception as e:
            logger.debug(f"Bible not found for book_id={book_id}: {e}")
            return None

    # 分割後のメソッドを公開（後方互換性のため）
    async def build_full_writing_context(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """執筆に必要な完全なコンテキストを構築する。（後方互換性のため公開）"""
        return await self._episode_writer.build_context(
            book_id, branch_id, ep_num, target_word_count, style_tag
        )

    async def write_episode(self, book_id: int, ep_num: int, context: Dict[str, Any]) -> str:
        """
        エピソード本文を生成し、文字列で返す。
        :param book_id: 書籍ID
        :param ep_num: エピソード番号
        :param context: プロット情報、キャラ設定、世界設定などを含む辞書
        :return: 生成された本文（文字列）
        """
        return await self._episode_writer.write(book_id, ep_num, context)

    async def generate_episodes(
        self,
        book_id,
        start_ep,
        end_ep,
        passion,
        target_word_count,
        is_easy_mode,
        reporter,
        branch_id=1,
        style_tag=None,
    ):
        """簡易エピソード生成。成功時は生成文字数（>0）を返す。失敗時は 0。"""
        # TODO: 新しいコンポーネントを使うように実装を更新
        total_chars = 0
        for ep in range(start_ep, end_ep + 1):
            try:
                ctx = await self.build_full_writing_context(
                    book_id=book_id,
                    branch_id=branch_id,
                    ep_num=ep,
                    target_word_count=target_word_count,
                    style_tag=style_tag,
                )
                text = await self.write_episode(book_id, ep, ctx)
                total_chars += len(text)
            except Exception as e:
                logger.error(f"generate_episodes failed at ep {ep}: {e}")
                return 0
        return total_chars

    async def generate_episodes_pipeline(
        self,
        book_id,
        start_ep,
        end_ep,
        passion,
        target_word_count,
        is_easy_mode,
        reporter,
        branch_id=1,
        style_tag=None,
    ):
        """エピソード生成パイプライン。成功時は (total_chars, []) 、失敗時は (0, [failed_eps]) を返す。"""
        # TODO: 新しいコンポーネントを使うように実装を更新
        pipeline = EpisodePipeline(self)
        return await pipeline.run(
            book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode, reporter, branch_id, style_tag
        )

    async def trigger_bible_extraction(self, book_id, content, reporter):
        """Bible抽出トリガー（現在はスタブ）"""
        # TODO: 新しいコンポーネントを使うように実装を更新
        return await self._bible_extractor.extract(book_id, content, reporter)

    async def run(self, *args, **kwargs):
        """エージェントのメインループ（簡易版）。
        ここでは generate_episodes と連動して実行する。
        """
        book_id = kwargs.get("book_id")
        start_ep = kwargs.get("start_ep")
        end_ep = kwargs.get("end_ep")
        if book_id is None or start_ep is None or end_ep is None:
            raise ValueError("book_id, start_ep, end_ep are required for WritingAgent.run")
        passion = kwargs.get("passion", 0.5)
        target_word_count = kwargs.get("target_word_count", 2000)
        return await self.generate_episodes(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=kwargs.get("is_easy_mode", False),
            reporter=kwargs.get("reporter"),
            branch_id=kwargs.get("branch_id", 1),
            style_tag=kwargs.get("style_tag"),
        )
