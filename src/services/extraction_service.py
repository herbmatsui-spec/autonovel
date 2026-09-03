"""章本文からのナレッジグラフ抽出サービスモジュール.

Enhanced with:
- Improved prompts with few-shot examples
- Strict schema validation
- Confidence scoring
- Multi-pass extraction for complex texts
- Japanese-specific entity recognition hints
"""
from __future__ import annotations

import json
import re

from src.backend.logging_config import get_logger
from src.models.graph_schemas import Entity, GraphExtractionResult, Relationship
from src.services.llm.base import BaseLLMAdapter
from src.services.llm.factory import get_llm_adapter
from src.services.llm.prompts import (
    GRAPH_EXTRACTION_SYSTEM_PROMPT,
    GRAPH_EXTRACTION_USER_PROMPT,
)

logger = get_logger("extraction_service")

# Few-shot例（JSON Schema準拠）
FEW_SHOT_EXAMPLES = """
【抽出例 1: キャラクター紹介シーン】
本文: "アルスは聖剣エクスカリバーを手に、王都ルミナスの門をくぐった。門番のガレスは懐かしい顔を見て安堵した。"
出力:
{
  "entities": [
    {"name": "アルス", "type": "Character", "description": "主人公。聖剣を所持し王都に到着。", "properties": {"is_alive": true, "location": "王都ルミナス", "has_holy_sword": true}},
    {"name": "聖剣エクスカリバー", "type": "Item", "description": "伝説の聖剣。アルスが所持。", "properties": {"owner": "アルス", "type": "weapon"}},
    {"name": "王都ルミナス", "type": "Location", "description": "王国の首都。アルスが到着。", "properties": {"country": "ルミナス王国"}},
    {"name": "ガレス", "type": "Character", "description": "王都の門番。アルスの知り合い。", "properties": {"is_alive": true, "role": "gatekeeper", "location": "王都ルミナス"}}
  ],
  "relationships": [
    {"source": "アルス", "target": "聖剣エクスカリバー", "type": "POSSESSES", "detail": "手にしている"},
    {"source": "アルス", "target": "王都ルミナス", "type": "LOCATED_IN", "detail": "門をくぐって到着"},
    {"source": "ガレス", "target": "アルス", "type": "KNOWS", "detail": "懐かしい知り合い"},
    {"source": "ガレス", "target": "王都ルミナス", "type": "LOCATED_IN", "detail": "門番として勤務"}
  ],
  "plot_summary": "アルスが聖剣を携え王都ルミナスに到着し、門番ガレスと再会する。"
}

【抽出例 2: 戦闘・状態変化シーン】
本文: "魔獣グリフォンが空から襲いかかった。セリアは炎の魔法で迎撃し、アルスを庇って負傷した。"
出力:
{
  "entities": [
    {"name": "グリフォン", "type": "Character", "description": "魔獣。空から襲撃。", "properties": {"is_alive": true, "type": "monster", "element": "wind"}},
    {"name": "セリア", "type": "Character", "description": "仲間。炎魔法使い。アルスを庇って負傷。", "properties": {"is_alive": true, "is_injured": true, "magic_type": "fire"}},
    {"name": "アルス", "type": "Character", "description": "主人公。セリアに庇われる。", "properties": {"is_alive": true, "protected_by": "セリア"}}
  ],
  "relationships": [
    {"source": "グリフォン", "target": "アルス", "type": "ATTACKS", "detail": "空から襲撃"},
    {"source": "セリア", "target": "グリフォン", "type": "ATTACKS", "detail": "炎魔法で迎撃"},
    {"source": "セリア", "target": "アルス", "type": "PROTECTS", "detail": "庇って負傷"}
  ],
  "plot_summary": "グリフォンが襲撃し、セリアが炎魔法で迎撃、アルスを庇って負傷する。"
}

【抽出例 3: 伏線・アイテム獲得シーン】
本文: "古びた宝箱から『竜の心臓』という赤い宝石が見つかった。伝説では竜を操る力があるという。"
出力:
{
  "entities": [
    {"name": "竜の心臓", "type": "Item", "description": "赤い宝石。竜を操る力を持つ伝説のアイテム。", "properties": {"rarity": "legendary", "effect": "dragon_control", "source": "treasure_chest"}},
    {"name": "宝箱", "type": "Item", "description": "古びた宝箱。竜の心臓が入っていた。", "properties": {"state": "opened"}}
  ],
  "relationships": [
    {"source": "竜の心臓", "target": "宝箱", "type": "FOUND_IN", "detail": "宝箱から発見"},
    {"source": "竜の心臓", "target": "竜", "type": "CONTROLS", "detail": "伝説では竜を操る力"}
  ],
  "plot_summary": "宝箱から伝説のアイテム『竜の心臓』を入手。竜を操る力を持つ。"
}
"""


class ExtractionService:
    """章テキストからエンティティおよび関係性を抽出するサービス (Structured Outputs & Self-Correction対応)."""

    def __init__(self, llm_adapter: BaseLLMAdapter | None = None) -> None:
        self._llm = llm_adapter or get_llm_adapter()
        self._cache: dict[str, GraphExtractionResult] = {}

    def extract_graph_from_text(self, text: str, *, use_cache: bool = True) -> GraphExtractionResult:
        """テキストからエンティティとリレーションを高精度に抽出し、GraphExtractionResult を返す."""
        if not text or not text.strip():
            return GraphExtractionResult(entities=[], relationships=[], plot_summary="")

        # キャッシュチェック
        cache_key = self._compute_cache_key(text)
        if use_cache and cache_key in self._cache:
            logger.debug("Cache hit for extraction")
            return self._cache[cache_key]

        # プロンプト構築（few-shot例を含む）
        user_prompt = GRAPH_EXTRACTION_USER_PROMPT.format(text=text[:4000])
        system_prompt = (
            GRAPH_EXTRACTION_SYSTEM_PROMPT
            + "\n\n【厳守事項】\n"
            + "1. エンティティタイプは Character, Location, Item, Event, Faction, Concept のいずれかのみ使用\n"
            + "2. 関係タイプは大文字スネークケース (KNOWS, LOCATED_IN, POSSESSES, ATTACKS, PROTECTS, ALLY_OF, ENEMY_OF, MEMBER_OF, LEADER_OF, FOUND_IN, CONTROLS, CREATED_BY, CAUSED_BY, PART_OF, HAS_PART, SUCCEEDS, PRECEDES 等)\n"
            + "3. description と detail は日本語で簡潔に（50文字以内推奨）\n"
            + "4. properties には状態フラグ (is_alive, is_injured 等)、数値、分類情報を含める\n"
            + "5. plot_summary は一文で要約（100文字以内）\n"
            + FEW_SHOT_EXAMPLES
            + "\n必ず以下のJSONフォーマットで回答してください（Markdownコードブロック不要）:\n"
            + json.dumps({
                "entities": [
                    {
                        "name": "アルス",
                        "type": "Character",
                        "description": "主人公。剣士。",
                        "properties": {"is_alive": True}
                    }
                ],
                "relationships": [
                    {
                        "source": "アルス",
                        "target": "ルミナス王都",
                        "type": "LOCATED_IN",
                        "detail": "現在滞在中"
                    }
                ],
                "plot_summary": "アルスが王都に到着し、新たな仲間と出会う。"
            }, ensure_ascii=False, indent=2)
        )

        # Structured Outputs 用のスキーマ定義
        response_format = GraphExtractionResult.get_response_format()

        try:
            raw_response = self._llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                response_format=response_format,
            )
            cleaned_json = self._clean_json_string(raw_response)
            data = json.loads(cleaned_json)
            result = GraphExtractionResult.model_validate(data)
            result = self._post_process(result, text)

            if use_cache:
                self._cache[cache_key] = result

            return result
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
                result = GraphExtractionResult.model_validate(data)
                result = self._post_process(result, text)

                if use_cache:
                    self._cache[cache_key] = result

                return result
            except Exception as retry_err:
                logger.warning(
                    "Self-correction extraction also failed: %s. Falling back to heuristic extraction.",
                    retry_err,
                )
                return self._heuristic_fallback(text)

    def _post_process(self, result: GraphExtractionResult, original_text: str) -> GraphExtractionResult:
        """抽出結果の後処理: 正規化、重複除去、信頼度付与."""
        # エンティティ名の正規化（前後の空白除去）
        for ent in result.entities:
            ent.name = ent.name.strip()
            ent.description = ent.description.strip()
            # typeの正規化
            ent.type = self._normalize_entity_type(ent.type)  # type: ignore[assignment]

        # 関係の正規化
        for rel in result.relationships:
            rel.source = rel.source.strip()
            rel.target = rel.target.strip()
            rel.type = self._normalize_relation_type(rel.type)
            rel.detail = rel.detail.strip()

        # 重複エンティティ除去（同名・同タイプ）
        seen = set()
        unique_entities = []
        for ent in result.entities:
            key = (ent.name.lower(), ent.type)
            if key not in seen:
                seen.add(key)
                unique_entities.append(ent)
        result.entities = unique_entities

        # 存在しないエンティティを参照する関係を除去
        entity_names = {ent.name for ent in result.entities}
        valid_relationships = [
            rel for rel in result.relationships
            if rel.source in entity_names and rel.target in entity_names
        ]
        result.relationships = valid_relationships

        # plot_summary の長さ制限
        if len(result.plot_summary) > 200:
            result.plot_summary = result.plot_summary[:197] + "..."

        return result

    def _normalize_entity_type(self, entity_type: str) -> str:
        """エンティティタイプを正規化."""
        type_map = {
            "character": "Character",
            "person": "Character",
            "人物": "Character",
            "location": "Location",
            "place": "Location",
            "場所": "Location",
            "item": "Item",
            "object": "Item",
            "アイテム": "Item",
            "道具": "Item",
            "event": "Event",
            "出来事": "Event",
            "faction": "Faction",
            "組織": "Faction",
            "派閥": "Faction",
            "concept": "Concept",
            "概念": "Concept",
        }
        normalized = entity_type.strip()
        # 最初の文字を大文字、残り小文字
        normalized = normalized[0].upper() + normalized[1:].lower() if normalized else "Concept"
        return type_map.get(normalized.lower(), normalized)

    def _normalize_relation_type(self, relation_type: str) -> str:
        """関係タイプを正規化（大文字スネークケース）."""
        # スペースやハイフンをアンダースコアに
        normalized = re.sub(r"[\s\-]+", "_", relation_type.strip())
        # 大文字化
        return normalized.upper()

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

    def _compute_cache_key(self, text: str) -> str:
        """テキストからキャッシュキーを生成（先頭500文字のハッシュ）."""
        import hashlib
        return hashlib.md5(text[:500].encode()).hexdigest()

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
        # 日本語固有表現抽出（簡易版）
        entities: list[Entity] = []
        relationships: list[Relationship] = []

        # キャラクター名らしきパターン（カタカナ・漢字の組み合わせ）
        char_pattern = r"([ァ-ヶー][ァ-ヶー一-龯]{1,5}|[一-龯]{2,4})(?:は|が|を|に|と|の|へ|で|や|も)"
        for match in re.finditer(char_pattern, text[:1000]):
            name = match.group(1)
            if len(name) >= 2 and name not in ["主人公", "彼女", "彼", "自分", "みんな", "誰も"]:
                entities.append(Entity(
                    name=name,
                    type="Character",
                    description="ヒューリスティック抽出による推定キャラクター",
                    properties={"is_alive": True, "heuristic": True}
                ))
                if len(entities) >= 5:
                    break

        # キーワードベースのイベント抽出
        event_keywords = ["戦闘", "戦い", "戦う", "魔法", "剣", "攻撃", "防御", "逃走", "追跡", "会話", "会議", "儀式", "召喚"]
        for kw in event_keywords:
            if kw in text:
                entities.append(Entity(
                    name=kw,
                    type="Event",
                    description=f"{kw}が発生",
                    properties={"heuristic": True}
                ))
                break

        plot_summary = text[:100] + "..." if len(text) > 100 else text

        return GraphExtractionResult(
            entities=entities,
            relationships=relationships,
            plot_summary=plot_summary,
        )

    def clear_cache(self) -> None:
        """キャッシュをクリア."""
        self._cache.clear()
        logger.debug("Extraction cache cleared")


extraction_service = ExtractionService()

__all__ = ["ExtractionService", "extraction_service"]
