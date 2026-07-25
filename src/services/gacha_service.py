import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

from pydantic import ValidationError

from src.models.easy_mode_schemas import (
    GachaPlan,
    GachaPlanType,
    GachaRequest,
    GachaResponse,
)
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# ガチャリクエスト結果の一時ストア（Digest生成用キャッシュ）
_GACHA_CACHE: Dict[str, Dict[str, Any]] = {}


class GachaService:
    """3案ガチャ生成サービス"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    async def generate_plans(self, request: GachaRequest) -> GachaResponse:
        """王道・変化球・ダークの3案企画を並列生成する"""
        if not request.genre or not request.keywords:
            raise ValueError("ジャンルとキーワードは必須です")

        request_id = f"gacha_{uuid.uuid4().hex[:8]}"

        types = [
            (GachaPlanType.ROYAL, "王道展開：読者の期待に100%応える爽快な展開"),
            (GachaPlanType.CURVEBALL, "変化球展開：予想外のギャップや設定で魅せる奇抜な展開"),
            (GachaPlanType.DARK, "ダーク展開：シリアスで深みのある重厚な展開"),
        ]

        async def _generate_single_plan(plan_type: GachaPlanType, direction: str) -> GachaPlan:
            prompt = f"""
ジャンル: {request.genre}
キーワード: {", ".join(request.keywords)}
方針: {direction}

以下のJSON形式でWeb小説の企画案を1つ作成してください。
JSONキー:
- "title": 作品タイトル
- "logline": 1行あらすじ（50文字程度）
- "protagonist_summary": 主人公の属性・特徴（50文字程度）
- "charm_point": この案の最大の魅力（50文字程度）

必ずJSONフォーマットのみを出力してください。
"""
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    res = await self.llm_service.generate_json(
                        purpose="planning",
                        prompt=prompt,
                        temp=request.temperature,
                    )
                    content = res.get("story_content", {})
                    if isinstance(content, str):
                        content = json.loads(content)

                    plan_id = f"plan_{uuid.uuid4().hex[:6]}"
                    return GachaPlan(
                        plan_id=plan_id,
                        plan_type=plan_type,
                        title=content.get("title", f"{request.genre}【{plan_type.value}案】"),
                        logline=content.get("logline", "あらすじ準備中"),
                        protagonist_summary=content.get("protagonist_summary", "主人公詳細準備中"),
                        charm_point=content.get("charm_point", "魅力ポイント準備中"),
                    )
                except (ValidationError, json.JSONDecodeError, Exception) as e:
                    logger.warning(
                        f"Plan generation failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    if attempt == max_retries:
                        # フォールバックプラン
                        plan_id = f"plan_{uuid.uuid4().hex[:6]}"
                        return GachaPlan(
                            plan_id=plan_id,
                            plan_type=plan_type,
                            title=f"{request.genre}：{plan_type.value}の物語",
                            logline=f"{', '.join(request.keywords)}をモチーフにした{direction}",
                            protagonist_summary="個性的で魅力的な主人公",
                            charm_point=f"{plan_type.value}ならではの怒涛の展開",
                        )

        try:
            tasks = [_generate_single_plan(pt, direction) for pt, direction in types]
            plans = await asyncio.wait_for(asyncio.gather(*tasks), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error("Gacha generation timed out (30s)")
            raise TimeoutError("企画の生成処理がタイムアウトしました")

        response = GachaResponse(request_id=request_id, plans=list(plans))

        # キャッシュに保存
        _GACHA_CACHE[request_id] = {
            "request": request.model_dump(),
            "response": response.model_dump(),
        }

        return response
