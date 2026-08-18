import logging
from typing import Optional

from prompts.afterglow_prompts import build_afterglow_prompt
from src.schemas.ux_schemas import MonologueResponse

logger = logging.getLogger(__name__)


class AfterglowGenerator:
    """エピソード終了後の余韻・裏視点キャラクター独白を生成するエージェント"""

    def __init__(self, llm_gateway: Optional[object] = None) -> None:
        self.llm_gateway = llm_gateway

    async def generate_monologue(self, character_name: str, scene_type: str, context: str = "") -> MonologueResponse:
        prompt = build_afterglow_prompt(character_name, scene_type, context)
        
        if self.llm_gateway and hasattr(self.llm_gateway, "generate_text"):
            try:
                res = await self.llm_gateway.generate_text(purpose="afterglow", prompt=prompt)
                content = res if isinstance(res, str) else getattr(res, "story_content", str(res))
                return MonologueResponse(
                    character_name=character_name,
                    scene_type=scene_type,
                    inner_monologue=content,
                    sentiment_tag="vulnerable_affection",
                )
            except Exception as e:
                logger.warning(f"LLM Afterglow generation failed, fallback: {e}")

        # 高品質なテンプレートフォールバック
        fallback_monologues = {
            "メインヒロイン": (
                "（……あんな真剣な目で見つめられたら、断れるわけないじゃない。"
                "『大丈夫だ』って言われた瞬間、ずっと張り詰めてた胸がぎゅって苦しくなって……。"
                "ほんと、ずるい人。私の全部、見透かされてるみたい……）"
            ),
            "ライバル令嬢": (
                "（わたくしとしたことが、あのような無様を晒すなんて……！"
                "でも……あの男、わたくしを嘲笑うでもなく、ただ当然のように庇って……。"
                "礼など絶対に言いませんわ。……でも、次会ったときは、少しだけ紅茶を淹れてあげてもよろしくてよ）"
            ),
        }

        monologue = fallback_monologues.get(
            character_name,
            f"（……信じられない。{character_name}の心は、あの瞬間から激しく揺さぶられたまま戻らない……）"
        )

        return MonologueResponse(
            character_name=character_name,
            scene_type=scene_type,
            inner_monologue=monologue,
            sentiment_tag="tsundere_deredere_transition",
        )
