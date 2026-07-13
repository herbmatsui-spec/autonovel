# agents/writing.py
import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.core.interfaces import IPromptManager
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class WritingAgent(BaseAgent):
    """執筆を担当するエージェント。
    プロンプトマネージャと LLM サービスを使用して、エピソード本文を生成する。
    """
    def __init__(self, repo: Any = None, llm: Optional[LLMService] = None, prompt_manager: Optional[IPromptManager] = None, style_rag: Any = None, rag_prefetch: Any = None):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.prompt_manager = prompt_manager

    async def write_episode(self, book_id: int, ep_num: int, context: Dict[str, Any]) -> str:
        """
        エピソード本文を生成し、文字列で返す。
        :param book_id: 書籍ID
        :param ep_num: エピソード番号
        :param context: プロット情報、キャラ設定、世界設定などを含む辞書
        :return: 生成された本文（文字列）
        """
        # プロンプトを構築
        if self.prompt_manager is None:
            raise ValueError("PromptManager is not injected into WritingAgent")
        prompt = self.prompt_manager.build_final_writing_prompt(
            ep_num=ep_num,
            plot_data=context.get("plot", {}),
            script_text=context.get("script", ""),
            target_word_count=context.get("target_word_count", 2000),
            **context
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

        # LLM で本文生成
        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
        )

        if specialist and erotic_intensity > 0 and nsfw_enabled:
            try:
                result = specialist.metaphor_filter(result, erotic_intensity)
            except Exception as e:
                logger.warning(f"metaphor_filter failed: {e}")

            # afterglow 必須項目の検証
            try:
                from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
                evaluator = AfterglowEvaluator()
                # テキストの最後1/4を afterglow 傾向として検証
                afterglow_candidate = result[len(result) * 3 // 4:]
                afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)
                if not afterglow_ok:
                    logger.warning(
                        f"Episode {ep_num} afterglow quality issues: {afterglow_issues}. "
                        "Consider regeneration or supplementation."
                    )
            except Exception as e:
                logger.warning(f"Afterglow evaluation failed: {e}")

        # 結果をログに残す
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

    async def generate_episodes(self, book_id, start_ep, end_ep, passion, target_word_count, is_easy_mode, reporter, branch_id=1, style_tag=None):
        """簡易エピソード生成。成功時は生成文字数（>0）を返す。失敗時は 0。"""
        total_chars = 0
        for ep in range(start_ep, end_ep + 1):
            ctx = {
                "plot": {"branch_id": branch_id, "ep_num": ep},
                "target_word_count": target_word_count,
                "style_tag": style_tag,
            }
            try:
                text = await self.write_episode(book_id, ep, ctx)
                total_chars += len(text)
            except Exception as e:
                logger.error(f"generate_episodes failed at ep {ep}: {e}")
                return 0
        return total_chars

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

