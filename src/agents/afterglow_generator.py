import logging
from typing import Any, Optional

from prompts.afterglow_prompts import build_afterglow_prompt
from src.schemas.ux_schemas import MonologueResponse

logger = logging.getLogger(__name__)


class AfterglowGenerator:
    """エピソード終了後の余韻・裏視点キャラクター独白を生成するエージェント"""

    def __init__(
        self,
        llm_gateway: Optional[object] = None,
        bible_service: Optional[Any] = None,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.bible_service = bible_service

    async def generate_monologue(
        self,
        character_name: str,
        scene_type: str,
        context: str = "",
        affinity_data: Optional[object] = None,
        book_id: Optional[int] = None,
    ) -> MonologueResponse:
        mood = getattr(affinity_data, "current_mood", None)
        if isinstance(affinity_data, dict):
            mood = affinity_data.get("current_mood", mood)

        char_ctx_str = ""
        if self.bible_service and book_id:
            try:
                ctx = await self.bible_service.get_context_by_book_id(book_id)
                if ctx:
                    char_obj = ctx.get_character(character_name)
                    if char_obj:
                        char_ctx_str = (
                            f"- 口調/語尾: {char_obj.tone or char_obj.suffix_style}\n"
                            f"- 一人称: {char_obj.first_person} / 二人称: {char_obj.second_person}\n"
                            f"- 表の顔と裏の真実: {char_obj.social_mask_vs_truth}\n"
                            f"- 隠された秘密: {', '.join(char_obj.secrets) if char_obj.secrets else 'なし'}"
                        )
            except Exception as e:
                logger.warning(f"Failed to fetch Bible context for Afterglow: {e}")

        prompt = build_afterglow_prompt(
            character_name,
            scene_type,
            context,
            mood=mood,
            character_context=char_ctx_str,
        )

        if self.llm_gateway and hasattr(self.llm_gateway, "generate_text"):
            try:
                res = await self.llm_gateway.generate_text("afterglow", prompt=prompt)
                content = res if isinstance(res, str) else getattr(res, "story_content", str(res))
                return MonologueResponse(
                    character_name=character_name,
                    scene_type=scene_type,
                    inner_monologue=content,
                    sentiment_tag=mood or "vulnerable_affection",
                )
            except Exception as e:
                logger.warning(f"LLM Afterglow generation failed, fallback: {e}")

        # 心理状態（mood）に応じた高品質なテンプレートフォールバック
        fallback_by_mood = {
            "wary": "（……信じられない。あの男、何を企んでいるの？ でも……あの瞳、嘘をついているようには見えなかった……）",
            "tsundere": (
                "（……あんな真剣な目で見つめられたら、怒る気も失せるじゃない。"
                "『お前が無事でよかった』だなんて……ばか。私の全部、見透かされてるみたいで悔しい……）"
            ),
            "affectionate": (
                "（……温かいな。そばにいるだけで、胸の奥がじんわり熱くなる。"
                "ずっと言えなかった『ありがとう』、次こそはちゃんと目を見て伝えよう……）"
            ),
            "deep_love": (
                "（……もう、あなたなしの世界なんて考えられない。"
                "誰にも渡さない。私の全部で、あなたを守り抜いてみせるから……）"
            ),
            "observation": "（……予想以上の器量ね。あの状況で迷わず動けるなんて。もう少し、近くで観察させてもらうわ）",
        }

        monologue = fallback_by_mood.get(
            mood,
            f"（……信じられない。{character_name}の心は、あの瞬間から激しく揺さぶられたまま戻らない……）"
        )

        return MonologueResponse(
            character_name=character_name,
            scene_type=scene_type,
            inner_monologue=monologue,
            sentiment_tag=mood or "vulnerable_affection",
        )

