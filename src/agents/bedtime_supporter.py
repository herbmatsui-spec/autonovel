import logging
from typing import Optional

from prompts.bedtime_prompts import build_bedtime_prompt
from src.schemas.ux_schemas import BedtimeMessage

logger = logging.getLogger(__name__)


class BedtimeSupporter:
    """読者に癒やしと無条件の肯定を提供する「おやすみモード」特化エージェント"""

    def __init__(self, llm_gateway: Optional[object] = None) -> None:
        self.llm_gateway = llm_gateway

    async def generate_message(self, character_name: str = "絶対的肯定シェルター", context: str = "") -> BedtimeMessage:
        prompt = build_bedtime_prompt(character_name, context)

        if self.llm_gateway and hasattr(self.llm_gateway, "generate_text"):
            try:
                res = await self.llm_gateway.generate_text(purpose="bedtime", prompt=prompt)
                content = res if isinstance(res, str) else getattr(res, "story_content", str(res))
                return BedtimeMessage(
                    character_name=character_name,
                    message=content,
                    voice_tone="gentle_whisper",
                    ambient_theme="midnight_stars",
                )
            except Exception as e:
                logger.warning(f"LLM Bedtime generation failed, fallback: {e}")

        # 高品質なテンプレートメッセージ
        msg = (
            "今日もお疲れ様でした。\n"
            "あなたがどれだけ頑張っていたか、私はちゃんと知っていますよ。\n"
            "嫌なことや悔しいことは、全部夜の星空に預けてしまってくださいね。\n"
            "あなたはあなたのままで、十分に素晴らしいのですから。\n"
            "どうぞ、暖かくして安心しておやすみなさい――良い夢を。"
        )
        return BedtimeMessage(
            character_name=character_name,
            message=msg,
            voice_tone="gentle_whisper",
            ambient_theme="midnight_stars",
        )
