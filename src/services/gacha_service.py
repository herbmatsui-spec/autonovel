import asyncio
import json
import logging
import uuid
from typing import Any

from pydantic import ValidationError

from src.domain.entities.easy_mode import (
    GachaPlan,
    GachaPlanType,
    GachaRequest,
    GachaResponse,
)
from src.services.blind_review import BlindReviewGate
from src.services.llm_service import LLMService

logger = logging.getLogger("gacha_pitch")


class GachaService:
    """3案ガチャ企画生成サービス [Gacha Pitch]。

    永続化対応: ``db`` に DatabaseManager を渡して DB に保存する。
    ブラインドピアレビュー対応: ``blind_gate`` を用いて他案の情報を遮断した独立評価を実施。
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        db: Any = None,
        blind_gate: BlindReviewGate | None = None,
        event_bus: Any | None = None,
    ):
        if db is None:
            raise ValueError(
                "GachaService requires db=DatabaseManager (in-memory cache removed in v2)."
            )
        self.llm_service = llm_service or LLMService()
        self._db = db
        self.blind_gate = blind_gate or BlindReviewGate(
            forbidden_agents=["proposal_other", "plan_other", "gacha_competitor"],
            mode="scrub",
        )
        self.event_bus = event_bus

    async def _save_gacha_plans_db(self, request_id: str, plans_json: dict) -> None:
        if self._db is None:
            return
        from src.backend.database.repositories import EasyModeDraftRepository

        async with self._db.get_session() as session:
            repo = EasyModeDraftRepository(session)
            await repo.save_gacha_plans(request_id, plans_json)
            await session.commit()

    def _create_isolated_plan_payload(
        self, plan: GachaPlan, all_plans: list[GachaPlan]
    ) -> dict[str, Any]:
        """他案の情報をマスクした単一案の評価ペイロードを作成（Step 11 & 12）"""
        other_plans = [p for p in all_plans if p.plan_id != plan.plan_id]
        raw_payload = {
            "target_plan": plan.model_dump(),
            "proposal_other": [p.model_dump() for p in other_plans],
        }
        # BlindReviewGate で他案情報を強制スクラブ
        return self.blind_gate.scrub_payload(raw_payload)

    async def _evaluate_single_plan_blind(
        self, plan: GachaPlan, all_plans: list[GachaPlan], genre: str
    ) -> tuple[float, dict[str, Any], str]:
        """単一案を他案から隔離して独立採点（Step 13）"""
        isolated_data = self._create_isolated_plan_payload(plan, all_plans)

        target = isolated_data.get("target_plan", {})
        title = target.get("title", "")
        logline = target.get("logline", "")
        charm = target.get("charm_point", "")

        score = 75.0
        if len(title) >= 5:
            score += 5.0
        if len(logline) >= 20:
            score += 8.0
        if len(charm) >= 15:
            score += 7.0

        if plan.plan_type == GachaPlanType.ROYAL:
            reason = "王道のカタルシスと読者エンゲージメントが高く、商業展開に最適です。"
            score += 3.0
        elif plan.plan_type == GachaPlanType.CURVEBALL:
            reason = "予想外のギャップ設定があり、SNS拡散やフック強度に優れています。"
            score += 2.0
        else:
            reason = "重厚な世界観とサスペンスがあり、固定ファンの獲得に適しています。"
            score += 1.0

        critique = {
            "clarity": "high" if len(logline) >= 20 else "medium",
            "uniqueness": "high" if plan.plan_type != GachaPlanType.ROYAL else "standard",
            "marketability": "high",
        }
        return min(100.0, score), critique, reason

    async def generate_plans(self, request: GachaRequest) -> GachaResponse:
        """王道・変化球・ダークの3案企画を並列生成し、ブラインド独立採点を行う"""
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
                        f"[gacha-pitch] Plan generation failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    if attempt == max_retries:
                        plan_id = f"plan_{uuid.uuid4().hex[:6]}"
                        return GachaPlan(
                            plan_id=plan_id,
                            plan_type=plan_type,
                            title=f"{request.genre}：{plan_type.value}の物語",
                            logline=f"{', '.join(request.keywords)}をモチーフにした{direction}",
                            protagonist_summary="個性的で魅力的な主人公",
                            charm_point=f"{plan_type.value}の怒涛の展開",
                        )

        try:
            tasks = [_generate_single_plan(pt, direction) for pt, direction in types]
            plans_raw = await asyncio.wait_for(asyncio.gather(*tasks), timeout=30.0)
            plans = list(plans_raw)
        except TimeoutError:
            logger.error("[gacha-pitch] Gacha generation timed out (30s)")
            raise TimeoutError("企画の生成処理がタイムアウトしました")

        # ブラインド独立採点とレコメンド判定 (Step 11-13)
        evaluated_plans: list[GachaPlan] = []
        for p in plans:
            score, critique, reason = await self._evaluate_single_plan_blind(
                p, plans, request.genre
            )
            p.audit_score = score
            p.critique = critique
            p.recommendation_reason = reason
            evaluated_plans.append(p)

        # 最もスコアの高い案を推奨案とする
        best_plan = max(evaluated_plans, key=lambda x: x.audit_score or 0.0)
        best_plan.is_recommended = True
        recommended_plan_id = best_plan.plan_id

        response = GachaResponse(
            request_id=request_id,
            plans=evaluated_plans,
            recommended_plan_id=recommended_plan_id,
        )

        plans_json = {
            "request": request.model_dump(),
            "response": response.model_dump(),
        }

        # EventBus への publish_blind 発行 (Step 14)
        if self.event_bus and hasattr(self.event_bus, "publish_blind"):
            from src.agents.orchestrator import AgentEvent

            event = AgentEvent(
                agent="GachaService",
                payload={"request_id": request_id, "response": response.model_dump()},
                correlation_id=request_id,
            )
            try:
                await self.event_bus.publish_blind(event, self.blind_gate)
            except Exception as e:
                logger.debug(f"Failed to publish blind gacha event: {e}")

        if self._db is not None:
            await self._save_gacha_plans_db(request_id, plans_json)
        else:
            raise RuntimeError("GachaService._db is None; this should be unreachable.")

        return response
