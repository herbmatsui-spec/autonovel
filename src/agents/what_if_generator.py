import logging
from typing import Optional

from prompts.what_if_prompts import build_what_if_prompt
from src.schemas.ux_schemas import WhatIfRequest, WhatIfResponse

logger = logging.getLogger(__name__)


class WhatIfGenerator:
    """「もしも」IFルートの短編ストーリーを生成するエージェント"""

    def __init__(self, llm_gateway: Optional[object] = None) -> None:
        self.llm_gateway = llm_gateway

    async def generate_branch(self, req: WhatIfRequest) -> WhatIfResponse:
        prompt = build_what_if_prompt(req.choice_point, req.novel_context or "")
        
        if self.llm_gateway and hasattr(self.llm_gateway, "generate_text"):
            try:
                res = await self.llm_gateway.generate_text(purpose="what_if", prompt=prompt)
                content = res if isinstance(res, str) else getattr(res, "story_content", str(res))
                return WhatIfResponse(
                    choice_point=req.choice_point,
                    alternative_snippet=content,
                    outcome_summary="LLMにより動的生成された分岐ルート",
                    impact_level="critical",
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
        )
