"""上級者エディタ用 専属AI編集者（GraphRAG Q&A & 設定矛盾診断）サービスモジュール."""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from src.core.llm_gateway import LLMGateway
from src.engine.prompts.editorial_prompts import (
    ASK_BIBLE_PROMPT_TEMPLATE,
    CONSISTENCY_AUDIT_PROMPT_TEMPLATE,
    EDITORIAL_SYSTEM_INSTRUCTION,
)
from src.models.editor import (
    AskBibleRequest,
    AskBibleResponse,
    ConsistencyAuditRequest,
    ConsistencyAuditResponse,
    ConsistencyIssue,
    GraphEvidenceNode,
)
from src.services.rag_service import GraphRAGService

logger = logging.getLogger(__name__)


class EditorialAssistantService:
    """GraphRAG 統合・専属 AI 編集者サービス"""

    def __init__(
        self,
        rag_service: GraphRAGService | None = None,
        llm_gateway: LLMGateway | None = None,
    ):
        self.rag = rag_service or GraphRAGService()
        self.llm = llm_gateway or LLMGateway()

    async def ask_bible(self, session: Session, request: AskBibleRequest) -> AskBibleResponse:
        """世界観バイブル・過去章に対する Q&A を実行する"""
        entities = self._extract_entities(request.query)
        evidence_nodes = self._retrieve_evidence(session, request.book_id, entities, request.query)

        # 類似チャンクの検索 (ベクトル検索)
        similar_chunks = self.rag.search_similar_chunks(session, request.query, limit=3)

        evidence_text_parts = []
        if similar_chunks:
            evidence_text_parts.append("【過去章・設定抜粋】\n" + "\n---\n".join(similar_chunks))
        if evidence_nodes:
            node_desc = "\n".join(f"- [{n.label}] {n.id}: {n.properties}" for n in evidence_nodes)
            evidence_text_parts.append("【ナレッジグラフ確定事実】\n" + node_desc)

        evidence_text = (
            "\n\n".join(evidence_text_parts) if evidence_text_parts else "（関連設定データなし）"
        )
        character_text = ", ".join(entities) if entities else "（特になし）"

        prompt = ASK_BIBLE_PROMPT_TEMPLATE.format(
            evidence_text=evidence_text,
            character_text=character_text,
            query=request.query,
        )

        try:
            res = await self.llm.generate_text(
                purpose_or_request="editorial",
                prompt=prompt,
                system_instruction=EDITORIAL_SYSTEM_INSTRUCTION,
                temp=0.5,
            )
            answer = getattr(res, "story_content", "") or getattr(res, "content", "") or ""
            if not answer:
                answer = "設定資料を参照しましたが、該当する情報は見つかりませんでした。"
        except Exception as e:
            logger.error("AskBible LLM call failed: %s", e)
            answer = f"設定資料の検索結果: {evidence_text[:200]}..."

        return AskBibleResponse(
            answer=str(answer).strip(),
            evidence_nodes=evidence_nodes,
            related_characters=entities,
        )

    async def audit_consistency(
        self, session: Session, request: ConsistencyAuditRequest
    ) -> ConsistencyAuditResponse:
        """執筆テキストと GraphRAG 設定の矛盾・不整合をリアルタイム診断する"""
        entities = self._extract_entities(request.content)
        evidence_nodes = self._retrieve_evidence(
            session, request.book_id, entities, request.content
        )

        node_desc = (
            "\n".join(f"- [{n.label}] {n.id}: {n.properties}" for n in evidence_nodes)
            if evidence_nodes
            else "（既知のキャラクター・設定データなし）"
        )

        prompt = CONSISTENCY_AUDIT_PROMPT_TEMPLATE.format(
            evidence_text=node_desc,
            content=request.content[:1500],
        )

        try:
            res = await self.llm.generate_text(
                purpose_or_request="audit",
                prompt=prompt,
                system_instruction=EDITORIAL_SYSTEM_INSTRUCTION,
                temp=0.2,
            )
            raw_text = getattr(res, "story_content", "") or getattr(res, "content", "") or ""

            # JSON パース処理
            return self._parse_audit_json(str(raw_text))
        except Exception as e:
            logger.error("Audit consistency LLM call failed: %s", e)
            return ConsistencyAuditResponse(has_issues=False, issues=[], confidence_score=0.5)

    def _extract_entities(self, text: str) -> list[str]:
        """テキストから登場人物や固有名詞を簡易抽出する"""
        if not text:
            return []
        common_names = ["アルト", "アリス", "ルシアン", "エレナ", "魔王", "聖剣", "王都ルミナス"]
        found = [name for name in common_names if name in text]
        if not found and len(text) <= 20:
            found.append(text.strip())
        return found

    def _retrieve_evidence(
        self,
        session: Session,
        book_id: int,
        entities: list[str],
        query_text: str,
    ) -> list[GraphEvidenceNode]:
        """GraphRAG からノード情報を取得・Rerank する"""
        if not entities:
            return []

        try:
            raw_neighbors = self.rag.get_graph_context(session, entities, max_depth=2)
            reranked = self.rag.rerank_graph_neighbors(raw_neighbors, query_text, top_k=5)

            nodes: list[GraphEvidenceNode] = []
            for item in reranked:
                target_name = item.get("target_name") or item.get("id") or "Unknown"
                rel = item.get("relation") or item.get("label") or "RELATED_TO"
                props = item.get("properties") or {}
                nodes.append(
                    GraphEvidenceNode(
                        id=str(target_name),
                        label=str(rel),
                        properties=props if isinstance(props, dict) else {"detail": str(props)},
                        source_reference="ナレッジグラフ",
                    )
                )
            return nodes
        except Exception as e:
            logger.warning("Graph evidence retrieval fallback: %s", e)
            return [
                GraphEvidenceNode(
                    id=ent,
                    label="Character",
                    properties={"name": ent, "status": "active"},
                    source_reference="基本バイブル",
                )
                for ent in entities
            ]

    def _parse_audit_json(self, raw_text: str) -> ConsistencyAuditResponse:
        """LLM の出力から ConsistencyAuditResponse をパースする"""
        try:
            # Markdown コードブロックの除去
            cleaned = raw_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            data = json.loads(cleaned)
            issues = [
                ConsistencyIssue(
                    issue_type=item.get("issue_type", "attribute"),
                    severity=item.get("severity", "warning"),
                    description=item.get("description", ""),
                    conflicting_text=item.get("conflicting_text", ""),
                    suggested_fix=item.get("suggested_fix", ""),
                )
                for item in data.get("issues", [])
            ]
            return ConsistencyAuditResponse(
                has_issues=bool(data.get("has_issues", len(issues) > 0)),
                issues=issues,
                confidence_score=float(data.get("confidence_score", 1.0)),
            )
        except Exception as e:
            logger.debug("Failed to parse audit JSON: %s, raw: %s", e, raw_text)
            return ConsistencyAuditResponse(has_issues=False, issues=[], confidence_score=0.8)
