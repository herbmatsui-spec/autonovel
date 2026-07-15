# agents/writing.py
import json
import logging
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.agents.writing_scheduler import StreamingPlotScheduler
from src.core.interfaces import IPromptManager
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class WritingAgent(BaseAgent):
    """執筆を担当するエージェント。
    プロンプトマネージャと LLM サービスを使用して、エピソード本文を生成する。
    """
    def __init__(self, repo: Any = None, llm: Optional[LLMService] = None, prompt_manager: Optional[IPromptManager] = None, style_rag: Any = None, rag_prefetch: Any = None, plot_expander: Any = None):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.prompt_manager = prompt_manager
        self._plot_expander = plot_expander

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
            logger.debug(f"Previous chapter not found for book={book_id}, branch={branch_id}, ep={ep_num}: {e}")
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

    def _build_prev_ctx(self, prev_chapter: Optional[Any], book_id: int, branch_id: int, ep_num: int) -> str:
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

    async def build_full_writing_context(self, book_id: int, branch_id: int, ep_num: int, target_word_count: int, style_tag: Optional[str] = None) -> Dict[str, Any]:
        """執筆に必要な完全なコンテキストを構築する。"""
        plot = await self._get_plot(book_id, branch_id, ep_num)
        if plot is None:
            plot = await self._ensure_plot_exists(book_id, branch_id, ep_num)

        book = await self._get_book(book_id)
        chars = await self._get_chars(book_id)
        prev_chapter = await self._get_prev_chapter(book_id, branch_id, ep_num)

        active_chars = await self._get_active_chars(chars, plot)
        char_static_ctx = self._build_char_static_ctx(active_chars)
        char_dynamic_ctx = self._build_char_dynamic_ctx(active_chars, prev_chapter)
        prev_ctx = self._build_prev_ctx(prev_chapter, book_id, branch_id, ep_num)
        dialogue_profiles = self._build_dialogue_profiles(active_chars)

        plot_dict = {}
        if plot is not None:
            if hasattr(plot, "model_dump"):
                plot_dict = plot.model_dump()
            elif isinstance(plot, dict):
                plot_dict = plot
            else:
                plot_dict = {
                    "ep_num": ep_num,
                    "detailed_blueprint": getattr(plot, "detailed_blueprint", "") or "",
                    "scenes": getattr(plot, "scenes", []) or [],
                    "summary": getattr(plot, "summary", "") or "",
                    "current_chain_phase": getattr(plot, "current_chain_phase", "Friction") or "Friction",
                    "title": getattr(plot, "title", "") or "",
                    "tension": getattr(plot, "tension", 50) or 50,
                }
        else:
            plot_dict = {"ep_num": ep_num, "detailed_blueprint": "", "scenes": [], "summary": "", "current_chain_phase": "Friction"}

        pov_name = ""
        if active_chars:
            pov_name = getattr(active_chars[0], "name", "") or ""

        density_level = "Standard"
        if plot_dict.get("tension", 50) >= 80 or getattr(plot, "is_catharsis", False):
            density_level = "Extreme"
        elif plot_dict.get("tension", 50) >= 60:
            density_level = "High"

        return {
            "plot": plot_dict,
            "target_word_count": target_word_count,
            "style_tag": style_tag,
            "char_static_ctx": char_static_ctx,
            "char_dynamic_ctx": char_dynamic_ctx,
            "prev_ctx": prev_ctx,
            "pov_character_name": pov_name,
            "dialogue_profiles": dialogue_profiles,
            "density_level": density_level,
        }

    async def write_episode(self, book_id: int, ep_num: int, context: Dict[str, Any]) -> str:
        """
        エピソード本文を生成し、文字列で返す。
        :param book_id: 書籍ID
        :param ep_num: エピソード番号
        :param context: プロット情報、キャラ設定、世界設定などを含む辞書
        :return: 生成された本文（文字列）
        """
        if self.prompt_manager is None:
            raise ValueError("PromptManager is not injected into WritingAgent")

        plot_data = context.get("plot", {})
        if not plot_data.get("detailed_blueprint"):
            logger.warning(f"Ep.{ep_num}: detailed_blueprint is empty. Writing may be low quality.")

        script_text = context.get("script", "")
        prompt = await self.prompt_manager.build_final_writing_prompt(
            ep_num=ep_num,
            plot_data=plot_data,
            script_text=script_text,
            target_word_count=context.get("target_word_count", 2000),
            book_id=book_id,
            char_static_ctx=context.get("char_static_ctx", ""),
            char_dynamic_ctx=context.get("char_dynamic_ctx", ""),
            prev_ctx=context.get("prev_ctx", ""),
            pov_character_name=context.get("pov_character_name", ""),
            dialogue_profiles=context.get("dialogue_profiles", {}),
            density_level=context.get("density_level", "Standard"),
            style_tag=context.get("style_tag"),
        )

        erotic_intensity = context.get("erotic_intensity", 0)
        nsfw_enabled = context.get("nsfw_enabled", False)
        specialist = None

        if erotic_intensity > 0 and nsfw_enabled:
            try:
                from config.erotic_pacing import EroticCurve
                from src.engine.prompts.erotic_specialist import EroticSpecialist
                specialist = EroticSpecialist()
                curve = EroticCurve.create_default(erotic_intensity)
                peak_beat = curve.get_peak_beat()
                context["consent_state"] = peak_beat.consent_state if peak_beat else "implicit"
                erotic_prompt = specialist.build_scene_prompt(curve, context)
                prompt = prompt + "\n\n" + erotic_prompt
            except Exception as e:
                logger.warning(f"EroticSpecialist delegation failed, falling back: {e}")

        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
        )
        if hasattr(result, "story_content"):
            result = result.story_content

        if specialist and erotic_intensity > 0 and nsfw_enabled:
            try:
                result = specialist.metaphor_filter(result, erotic_intensity)
            except Exception as e:
                logger.warning(f"metaphor_filter failed: {e}")

            try:
                from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
                evaluator = AfterglowEvaluator()
                afterglow_candidate = result[len(result) * 3 // 4:]
                afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)
                if not afterglow_ok:
                    logger.warning(
                        f"Episode {ep_num} afterglow quality issues: {afterglow_issues}. "
                        "Consider regeneration or supplementation."
                    )
            except Exception as e:
                logger.warning(f"Afterglow evaluation failed: {e}")

        logger.info(
            f"Generated episode {ep_num} for book {book_id}, "
            f"length {len(result)} chars, "
            f"erotic_intensity={erotic_intensity}, nsfw={nsfw_enabled}"
        )
        return result

    @property
    def pm(self):
        return self.prompt_manager

    @property
    def planner(self):
        return getattr(self, "_planner", None)

    @planner.setter
    def planner(self, value):
        self._planner = value

    @property
    def plot_expander(self):
        return getattr(self, "_plot_expander", None)

    @plot_expander.setter
    def plot_expander(self, value):
        self._plot_expander = value

    async def generate_episodes(self, book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode, reporter, branch_id=1, style_tag=None):
        """簡易エピソード生成。成功時は生成文字数（>0）を返す。失敗時は 0。"""
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

    async def generate_episodes_pipeline(self, book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode, reporter, branch_id=1, style_tag=None):
        """エピソード生成パイプライン。成功時は (total_chars, []) 、失敗時は (0, [failed_eps]) を返す。"""
        total_chars = 0
        failed_episodes: List[Dict[str, Any]] = []

        scheduler = None
        arcs: List[Any] = []
        try:
            bible = await self._get_bible(book_id)
            if bible:
                settings = {}
                if hasattr(bible, "world_settings") and bible.world_settings:
                    settings = bible.world_settings
                elif hasattr(bible, "settings") and bible.settings:
                    if isinstance(bible.settings, str):
                        try:
                            settings = json.loads(bible.settings)
                        except Exception:
                            settings = {}
                    elif isinstance(bible.settings, dict):
                        settings = bible.settings
                arcs = settings.get("arcs", []) if isinstance(settings, dict) else []
        except Exception as e:
            logger.debug(f"Failed to get arcs for book_id={book_id}: {e}")

        if self.plot_expander is not None and arcs:
            try:
                scheduler = StreamingPlotScheduler(
                    repo=self.repo,
                    llm=self.llm,
                    pm=self.prompt_manager,
                    planner=self.plot_expander,
                    book_id=book_id,
                    branch_id=branch_id,
                    arcs=arcs,
                    end_ep=end_ep,
                    reporter=reporter,
                )
                if reporter:
                    reporter.report(f"🗺️ プロット先行スケジューラを起動 (arcs={len(arcs)})", "info")
            except Exception as e:
                logger.warning(f"Failed to initialize StreamingPlotScheduler: {e}")
                scheduler = None

        for ep in range(start_ep, end_ep + 1):
            try:
                if scheduler is not None:
                    try:
                        await scheduler.await_plot_ready(ep)
                    except Exception as e:
                        logger.warning(f"Scheduler await failed for Ep.{ep}: {e}")

                    if ep + 1 <= end_ep:
                        scheduler.schedule_plot_generation(ep + 1, None, {})
                    if ep + 2 <= end_ep:
                        scheduler.schedule_plot_generation(ep + 2, None, {})

                chars = await self.generate_episodes(
                    book_id=book_id,
                    start_ep=ep,
                    end_ep=ep,
                    passion=passion,
                    target_word_count=target_word_count,
                    is_easy_mode=is_easy_mode,
                    reporter=reporter,
                    branch_id=branch_id,
                    style_tag=style_tag,
                )
                if chars > 0:
                    total_chars += chars
                else:
                    failed_episodes.append({"ep_num": ep, "error_message": "0文字生成"})
            except Exception as e:
                logger.error(f"generate_episodes_pipeline failed at ep {ep}: {e}")
                failed_episodes.append({"ep_num": ep, "error_message": str(e)})

        if scheduler is not None:
            try:
                for task in scheduler.tasks.values():
                    if not task.done():
                        task.cancel()
            except Exception:
                pass

        return total_chars, failed_episodes

    async def trigger_bible_extraction(self, book_id, content, reporter):
        """Bible抽出トリガー（現在はスタブ）"""
        return None

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

