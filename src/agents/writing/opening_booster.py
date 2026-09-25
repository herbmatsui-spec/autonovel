"""
Opening Episode Booster Agent.
PLAN 02: 序盤3話特化型 ドーパミン注入・クリフハンガー強制エンジン
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING
import jinja2

from src.agents.base import BaseAgent
from src.config.opening_rules import GENRE_OPENING_TARGETS, OPENING_FORBIDDEN_RULES
from src.models.opening_booster import CliffhangerEvaluation, OpeningEpisodeConfig
from src.services.auditors.cliffhanger_scorer import score_cliffhanger

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OpeningBoosterAgent(BaseAgent):
    """第1話〜第3話特化型 執筆＆クリフハンガー強制エージェント"""

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        template_dir: str | Path | None = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        base_path = Path(__file__).resolve().parents[3] / "prompts" / "templates"
        self.template_dir = Path(template_dir) if template_dir else base_path
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def build_prompt(
        self,
        config: OpeningEpisodeConfig,
        protagonist_name: str = "主人公",
        genre: str = "異世界ファンタジー",
    ) -> str:
        """指定話数（1〜3話）に応じた特化プロンプトを構築する"""
        # ジャンル別テンプレートがあれば優先使用、なければ汎用テンプレートにフォールバック
        genre_template_name = f"narrative/opening_ep0{config.ep_num}_{genre}.j2"
        generic_template_name = f"narrative/opening_ep0{config.ep_num}.j2"
        try:
            template = self.jinja_env.get_template(genre_template_name)
        except jinja2.TemplateNotFound:
            try:
                template = self.jinja_env.get_template(generic_template_name)
            except jinja2.TemplateNotFound:
                logger.warning("Opening template %s/%s not found, falling back to ep01", genre_template_name, generic_template_name)
                template = self.jinja_env.get_template("narrative/opening_ep01.j2")

        target_instruction = GENRE_OPENING_TARGETS.get(genre, {}).get(config.ep_num, "")
        prompt = template.render(
            genre=genre,
            protagonist_name=protagonist_name,
            target_word_count=config.target_word_count,
            inciting_incident=config.inciting_incident,
            payoff_moment=config.payoff_moment,
            forbidden_rules=OPENING_FORBIDDEN_RULES,
            target_instruction=target_instruction,
        )
        return prompt

    async def generate_opening_episode(
        self,
        config: OpeningEpisodeConfig,
        protagonist_name: str = "主人公",
        genre: str = "異世界ファンタジー",
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """序盤エピソードを執筆し、クリフハンガー評価および必要に応じた自動リライトを実行する"""
        prompt = await self.build_prompt(
            config=config,
            protagonist_name=protagonist_name,
            genre=genre,
        )

        content = ""
        evaluation: CliffhangerEvaluation | None = None

        for attempt in range(max_retries + 1):
            logger.info("Generating opening episode %d (attempt %d)", config.ep_num, attempt + 1)
            raw_res = await self.llm.generate_text(purpose="writing", prompt=prompt)
            content = str(raw_res).strip()

            evaluation = score_cliffhanger(content)
            logger.info(
                "Cliffhanger evaluation for ep %d: type=%s, score=%.1f, rewrite=%s",
                config.ep_num,
                evaluation.hook_type.value,
                evaluation.score,
                evaluation.requires_rewrite,
            )

            if not evaluation.requires_rewrite or attempt == max_retries:
                break

            # リライト指示を付加して再生成
            rewrite_instruction = (
                f"\n\n【話末クリフハンガー修正指示（必須）】\n"
                f"現在の文章の終わり方は引きが弱く、読者が離脱してしまいます。\n"
                f"理由: {evaluation.reason}\n"
                f"話末（ラスト150文字）は必ず『敵の急襲』『衝撃の密命/真実の判明』『主人公の不敵な冷笑と反撃予告』のいずれかで締めくくり、次話を猛烈に読みたくなる強烈な引きを作ってください。"
            )
            prompt = prompt + rewrite_instruction

        return {
            "ep_num": config.ep_num,
            "content": content,
            "cliffhanger": evaluation,
        }

    async def run(self, ctx: Any) -> Any:
        """BaseAgent抽象メソッド実装"""
        logger.info("OpeningBoosterAgent run called")
        return None
