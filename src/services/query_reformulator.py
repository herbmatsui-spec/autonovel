"""Query Reformulator & HyDE Engine for Reflective RAG (Steps 25-27).

Transforms sparse keywords and scene intent into coherent, natural Japanese query sentences,
and generates hypothetical document embeddings (HyDE) to prevent semantic drift.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

QueryReformulationMode = Literal["hyde", "semantic_expansion", "intent_guided"]


class QueryReformulator:
    """Reformulates search queries into natural sentences and hypothetical passages."""

    def __init__(self, llm_adapter: Any = None) -> None:
        self.llm_adapter = llm_adapter

    def reformulate_query(
        self,
        query: str,
        keywords: list[str],
        scene_intent: str = "",
        mode: QueryReformulationMode = "intent_guided",
    ) -> str:
        """Reformulate query and keywords into a coherent natural language query."""
        if not keywords:
            return query

        clean_keywords = [k.strip() for k in keywords if k and k.strip()]
        if not clean_keywords:
            return query

        if mode == "hyde":
            return self.generate_hypothetical_chunk(query, keywords=clean_keywords)

        if mode == "semantic_expansion":
            # Expand with context connection
            kw_phrase = "、".join(clean_keywords[:4])
            return f"{query}に関する情報。特に関連する{kw_phrase}の詳細と設定。"

        # Default: intent_guided
        kw_phrase = "および".join(clean_keywords[:3])
        if scene_intent:
            return f"{scene_intent}を描くための{query}における{kw_phrase}に関する詳細設定。"
        return f"{query}における{kw_phrase}に関する設定や背景情報。"

    async def reformulate_query_async(
        self,
        query: str,
        keywords: list[str],
        scene_intent: str = "",
        mode: QueryReformulationMode = "intent_guided",
    ) -> str:
        """Asynchronously reformulate query using LLM if available, with sync fallback."""
        if self.llm_adapter and hasattr(self.llm_adapter, "generate"):
            try:
                kw_str = ", ".join(keywords)
                prompt = (
                    f"検索クエリ: {query}\n"
                    f"関連重要語: {kw_str}\n"
                    f"執筆シーン意図: {scene_intent or '世界観・設定の整合性確認'}\n"
                    "上記を踏まえ、小説の設定検索用として最も適切な1文の自然な検索クエリを生成してください。"
                )
                res = await self.llm_adapter.generate(prompt)
                if isinstance(res, str) and res.strip():
                    return res.strip()
            except Exception as e:
                logger.warning(f"LLM query reformulation failed ({e}), using rule-based.")

        return self.reformulate_query(query, keywords, scene_intent, mode)

    def generate_hypothetical_chunk(
        self,
        query: str,
        genre: str = "fantasy",
        keywords: list[str] | None = None,
    ) -> str:
        """Generate a hypothetical document passage (HyDE) matching the query."""
        kw_part = ""
        if keywords:
            kw_part = f"特に{'、'.join(keywords[:3])}に関する記述。"

        # Rule-based hypothetical document template
        return (
            f"【{genre.capitalize()}世界観アーカイブ】\n"
            f"{query}について：\n"
            f"本作の世界において、{query}は重要な役割を担っている。"
            f"{kw_part}\n"
            "これらは古くから体系化された伝承や記録として残されており、"
            "登場人物たちの行動や劇中の対立に直接影響を及ぼす。"
        )
