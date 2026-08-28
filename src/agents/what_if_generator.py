import logging
from typing import Any, Optional

from prompts.what_if_prompts import build_what_if_prompt
from src.schemas.ux_schemas import WhatIfRequest, WhatIfResponse

logger = logging.getLogger(__name__)


class WhatIfGenerator:
    """「もしも」IFルートの短編ストーリーを生成するエージェント"""

    def __init__(
        self,
        llm_gateway: Optional[object] = None,
        bible_service: Optional[Any] = None,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.bible_service = bible_service

    async def generate_branch(self, req: WhatIfRequest) -> WhatIfResponse:
        char_ctx_str = ""
        if self.bible_service and req.book_id:
            try:
                ctx = await self.bible_service.get_context_by_book_id(req.book_id)
                if ctx:
                    char_name = req.character_name or "mc"
                    char_obj = ctx.get_character(char_name)
                    if char_obj:
                        char_ctx_str = (
                            f"- 名前: {char_obj.name}\n"
                            f"- 性格: {char_obj.personality}\n"
                            f"- 鉄の掟: {char_obj.iron_constraint}\n"
                            f"- 表の顔と裏の真実: {char_obj.social_mask_vs_truth}\n"
                            f"- 一人称: {char_obj.first_person} / 二人称: {char_obj.second_person}"
                        )
            except Exception as e:
                logger.warning(f"Failed to fetch Bible context for WhatIf: {e}")

        prompt = build_what_if_prompt(
            req.choice_point,
            req.novel_context or "",
            character_context=char_ctx_str,
        )

        import hashlib
        cache_key = hashlib.md5(f"{req.book_id or 1}_{req.choice_point}_{req.character_name or ''}".encode()).hexdigest()[:12]

        if self.llm_gateway and hasattr(self.llm_gateway, "generate_text"):
            try:
                res = await self.llm_gateway.generate_text("what_if", prompt=prompt)
                content = res if isinstance(res, str) else getattr(res, "story_content", str(res))
                return WhatIfResponse(
                    choice_point=req.choice_point,
                    alternative_snippet=content,
                    outcome_summary="LLMにより動的生成された分岐ルート",
                    impact_level="critical",
                    branch_cache_key=cache_key,
                )
            except Exception as e:
                logger.warning(f"LLM What-If generation failed, fallback to template: {e}")

        # 高品質なテンプレートフォールバック
        snippet = (
            f"【運命の分岐】もし『{req.choice_point}』で別の道を選んでいたなら――\n\n"
            "主人公はあえて正面衝突を避け、影の路地に身を潜めた。\n"
            "傲慢な敵対者は無人の空間を切り裂き、苛立ちの咆哮を上げる。\n"
            "「どこへ消えた、卑怯者め！」\n"
            "その隙に主人公は敵の懐から決定的な機密文書を掠め取ることに成功していた。\n"
            "直接的なざまぁを後回しにしたことで、街全体を巻き込む巨大な陰謀の証拠が手に入ったのだ。"
        )
        return WhatIfResponse(
            choice_point=req.choice_point,
            alternative_snippet=snippet,
            outcome_summary="即時戦闘を回避し、敵の秘密を完全掌握するステルス・インテリジェンスルートへ突入。",
            impact_level="high",
            branch_cache_key=cache_key,
        )
