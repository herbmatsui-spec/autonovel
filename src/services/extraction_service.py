"""章本文からのナレッジグラフ抽出サービスモジュール."""
from __future__ import annotations

import json

from src.backend.logging_config import get_logger
from src.models.graph_schemas import Entity, GraphExtractionResult
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.factory import get_llm_adapter
from src.services.llm.prompts import (
    GRAPH_EXTRACTION_SYSTEM_PROMPT,
    GRAPH_EXTRACTION_USER_PROMPT,
)

logger = get_logger("extraction_service")


class ExtractionService:
    """章テキストからエンティティおよび関係性を抽出するサービス (Structured Outputs & Self-Correction対応)."""

    def __init__(self, llm_adapter: BaseLLMAdapter | None = None) -> None:
        self._llm = llm_adapter or get_llm_adapter()

    def extract_graph_from_text(self, text: str) -> GraphExtractionResult:
        """テキストからエンティティとリレーションを高精度に抽出し、GraphExtractionResult を返す."""
        if not text or not text.strip():
            return GraphExtractionResult(entities=[], relationships=[], plot_summary="")

        user_prompt = GRAPH_EXTRACTION_USER_PROMPT.format(text=text[:4000])  # トークン上限配慮
        system_prompt = (
            GRAPH_EXTRACTION_SYSTEM_PROMPT
            + "\n必ず以下のJSONフォーマットで回答してください:\n"
            + json.dumps(
                {
                    "entities": [
                        {
                            "name": "アルス",
                            "type": "Character",
                            "description": "主人公。剣士。",
                            "properties": {"is_alive": True},
                        }
                    ],
                    "relationships": [
                        {
                            "source": "アルス",
                            "target": "ルミナス王都",
                            "type": "LOCATED_IN",
                            "detail": "現在滞在中",
                        }
                    ],
                    "plot_summary": "アルスが王都に到着し、新たな仲間と出会う。",
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        # Structured Outputs 用のスキーマ定義
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "graph_extraction_result",
                "schema": GraphExtractionResult.model_json_schema(),
            },
        }

        try:
            raw_response = self._llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,  # 抽出は低温度で決定論的に
                response_format=response_format,
            )
            cleaned_json = self._clean_json_string(raw_response)
            data = json.loads(cleaned_json)
            return GraphExtractionResult.model_validate(data)
        except Exception as primary_err:
            logger.warning(
                "Primary graph extraction failed: %s. Attempting self-correction retry...",
                primary_err,
            )

            # Self-Correction リトライ
            try:
                correction_prompt = (
                    f"前回の出力でJSONパースエラーまたはスキーマ検証エラーが発生しました: {primary_err}\n"
                    f"以下の章本文から、再度厳密に指定スキーマのJSONのみを出力してください。\n\n"
                    f"【本文】\n{text[:3000]}"
                )
                corrected_response = self._llm.generate(
                    prompt=correction_prompt,
                    system_prompt=system_prompt,
                    temperature=0.1,
                    response_format=response_format,
                )
                cleaned_json = self._clean_json_string(corrected_response)
                data = json.loads(cleaned_json)
                return GraphExtractionResult.model_validate(data)
            except Exception as retry_err:
                logger.warning(
                    "Self-correction extraction also failed: %s. Falling back to heuristic extraction.",
                    retry_err,
                )
                return self._heuristic_fallback(text)

    def _clean_json_string(self, text: str) -> str:
        """Markdown コードブロック ```json ... ``` を取り除いて純粋な JSON 文字列にする."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _heuristic_fallback(self, text: str) -> GraphExtractionResult:
        """LLM呼び出し失敗時やモック環境でのヒューリスティック抽出フォールバック."""
        return GraphExtractionResult(
            entities=[
                Entity(name="主人公", type="Character", description="物語の中心人物", properties={"is_alive": True})
            ],
            relationships=[],
            plot_summary=text[:100] + "..." if len(text) > 100 else text,
        )


extraction_service = ExtractionService()

__all__ = ["ExtractionService", "extraction_service"]
