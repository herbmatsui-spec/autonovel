"""上級者エディタ用 Next Beats 3バリエーション分岐生成サービスモジュール."""

from __future__ import annotations

import asyncio
import json
import logging

from src.core.llm_gateway import LLMGateway
from src.engine.prompts.next_beats_prompts import (
    BRANCH_PROMPTS,
    NEXT_BEATS_SYSTEM_INSTRUCTION,
    NEXT_BEATS_USER_PROMPT_TEMPLATE,
)
from src.models.editor import (
    BeatCard,
    BranchType,
    NextBeatsRequest,
    NextBeatsResponse,
)

logger = logging.getLogger(__name__)


class NextBeatsService:
    """Next Beats 3バリエーション分岐並列生成サービス"""

    def __init__(self, llm_gateway: LLMGateway | None = None):
        self.llm = llm_gateway or LLMGateway()

    async def generate_three_beats(self, request: NextBeatsRequest) -> NextBeatsResponse:
        """王道・サスペンス・心情の3バリエーションを並列生成する"""
        tail_text = (
            request.current_text[-800:] if len(request.current_text) > 800 else request.current_text
        )

        branch_configs = [
            ("card_a", BranchType.ROYAL, "【王道】逆転の一撃"),
            ("card_b", BranchType.TWIST, "【急展開】予期せぬ影"),
            ("card_c", BranchType.PSYCHOLOGY, "【心情】交錯する想い"),
        ]

        tasks = [
            self._generate_single_beat(
                card_id=cid,
                branch_type=btype,
                default_title=def_title,
                current_tail=tail_text,
                genre=request.genre,
                character_context=request.character_context,
                temperature=request.temperature,
            )
            for cid, btype, def_title in branch_configs
        ]

        # 並列実行 (1つが失敗しても他は続行)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        cards: list[BeatCard] = []
        for i, res in enumerate(results):
            cid, btype, def_title = branch_configs[i]
            if isinstance(res, Exception):
                logger.error(f"Beat generation failed for {btype}: {res}")
                cards.append(
                    BeatCard(
                        card_id=cid,
                        branch_type=btype,
                        title=def_title,
                        summary="生成中に一時的なエラーが発生しました。再試行してください。",
                        content="（このバリエーションの生成に失敗しました。再生成ボタンをお試しください）",
                        hook_text="",
                    )
                )
            else:
                cards.append(res)

        return NextBeatsResponse(
            beats=cards,
            original_tail=tail_text[-200:] if tail_text else "",
        )

    async def _generate_single_beat(
        self,
        card_id: str,
        branch_type: BranchType,
        default_title: str,
        current_tail: str,
        genre: str,
        character_context: str,
        temperature: float = 0.8,
    ) -> BeatCard:
        """単一の展開バリエーションカードを生成する"""
        branch_inst = BRANCH_PROMPTS.get(branch_type, BRANCH_PROMPTS[BranchType.ROYAL])
        prompt = NEXT_BEATS_USER_PROMPT_TEMPLATE.format(
            current_tail=current_tail,
            genre=genre,
            character_context=character_context or "（特筆すべき制約なし）",
            branch_instruction=branch_inst,
        )

        try:
            res = await self.llm.generate_text(
                purpose_or_request="writing",
                prompt=prompt,
                system_instruction=NEXT_BEATS_SYSTEM_INSTRUCTION,
                temp=temperature,
            )
            raw_text = getattr(res, "story_content", "") or getattr(res, "content", "") or ""
            return self._parse_beat_json(str(raw_text), card_id, branch_type, default_title)
        except Exception as e:
            logger.error(f"Single beat generation failed ({branch_type}): {e}")
            raise

    def _parse_beat_json(
        self,
        raw_text: str,
        card_id: str,
        branch_type: BranchType,
        default_title: str,
    ) -> BeatCard:
        """LLM の JSON 出力をパースして BeatCard を構築する"""
        try:
            cleaned = raw_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            data = json.loads(cleaned)
            return BeatCard(
                card_id=card_id,
                branch_type=branch_type,
                title=data.get("title") or default_title,
                summary=data.get("summary") or "次の展開案",
                content=data.get("content") or raw_text[:300],
                hook_text=data.get("hook_text") or "",
            )
        except Exception as e:
            logger.debug(f"JSON parse fallback for BeatCard: {e}")
            # JSON パース失敗時は生のテキストを本文に割り当て
            return BeatCard(
                card_id=card_id,
                branch_type=branch_type,
                title=default_title,
                summary="次シーンの提案",
                content=raw_text.strip()[:400] if raw_text else "（展開案）",
                hook_text="",
            )
