"""章本文からのナレッジグラフ抽出サービスモジュール."""
from __future__ import annotations

import json

from src.backend.logging_config import get_logger
from src.models.graph_schemas import Entity, GraphExtractionResult, Relationship
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
        response_format = GraphExtractionResult.get_response_format()

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

    def resolve_entities(
        self,
        extracted: GraphExtractionResult,
        existing_entity_names: list[str],
        similarity_threshold: float = 0.85,
    ) -> GraphExtractionResult:
        """既存エンティティ名と新規抽出エンティティを照合し、表記揺れ（例: 'アルス' と '勇者アルス'）を既存名に名寄せする."""
        if not existing_entity_names or not extracted.entities:
            return extracted

        from src.services.embedding_service import embedding_service

        # 既存エンティティ名のベクトル化キャッシュ
        existing_vecs = {
            name: embedding_service.get_embedding(name) for name in existing_entity_names if name.strip()
        }

        # 新規エンティティ名の置換マップ
        name_map: dict[str, str] = {}
        for entity in extracted.entities:
            if entity.name in existing_vecs:
                continue  # 完全一致はそのまま

            ent_vec = embedding_service.get_embedding(entity.name)
            best_match: str | None = None
            best_sim = 0.0

            for ex_name, ex_vec in existing_vecs.items():
                # 単純な内包チェック（例: "アルス" in "勇者アルス"）も考慮
                if entity.name in ex_name or ex_name in entity.name:
                    best_match = ex_name
                    break

                # コサイン類似度
                dot = sum(a * b for a, b in zip(ent_vec, ex_vec))
                norm_a = sum(a * a for a in ent_vec) ** 0.5
                norm_b = sum(b * b for b in ex_vec) ** 0.5
                sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

                if sim > best_sim and sim >= similarity_threshold:
                    best_sim = sim
                    best_match = ex_name

            if best_match:
                logger.info("Entity resolved: '%s' -> '%s' (similarity: %.2f)", entity.name, best_match, best_sim)
                name_map[entity.name] = best_match

        if not name_map:
            return extracted

        # エンティティおよびリレーションの名前を置換して統合
        new_entities = []
        seen_names = set()
        for ent in extracted.entities:
            resolved_name = name_map.get(ent.name, ent.name)
            if resolved_name not in seen_names:
                seen_names.add(resolved_name)
                new_entities.append(
                    Entity(
                        name=resolved_name,
                        type=ent.type,
                        description=ent.description,
                        properties=ent.properties,
                    )
                )

        new_relationships = []
        for rel in extracted.relationships:
            new_relationships.append(
                Relationship(
                    source=name_map.get(rel.source, rel.source),
                    target=name_map.get(rel.target, rel.target),
                    type=rel.type,
                    detail=rel.detail,
                )
            )

        return GraphExtractionResult(
            entities=new_entities,
            relationships=new_relationships,
            plot_summary=extracted.plot_summary,
        )

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
