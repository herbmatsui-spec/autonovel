"""Local LLM Refiner for localized cadence and rhythm improvement."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from src.services.cadence.models import CadenceIntelligentConfig
from src.services.cadence.compound_merger import CompoundSentenceMerger
from src.services.cadence.span_extractor import TargetSpan

logger = logging.getLogger(__name__)


class LocalLLMCadenceRefiner:
    """Refines target violation spans using lightweight LLM with robust fallback."""

    def __init__(
        self,
        llm_client: Any = None,
        config: Optional[CadenceIntelligentConfig] = None,
        template_dir: Optional[Path] = None,
    ) -> None:
        self.llm_client = llm_client
        self.config = config or CadenceIntelligentConfig()
        self.merger = CompoundSentenceMerger(max_chars=self.config.max_compound_chars)

        if template_dir is None:
            # プロジェクトルートの prompts/templates/polish を探索
            current_file = Path(__file__).resolve()
            proj_root = current_file.parent.parent.parent.parent
            template_dir = proj_root / "prompts" / "templates" / "polish"

        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.jinja_env.get_template("local_cadence_refine.j2")

    def build_prompt(self, span: TargetSpan, is_past_locked: bool) -> str:
        """Render the refinement prompt for the given span."""
        return self.template.render(
            preceding_context=span.preceding_context,
            target_text=span.target_text,
            following_context=span.following_context,
            is_past_locked=is_past_locked,
        )

    def fallback_refine(self, span: TargetSpan) -> str:
        """Fallback refinement using CompoundSentenceMerger without LLM."""
        sentences = list(span.target_sentences)
        if len(sentences) == 2:
            merged = self.merger.merge_sentences(sentences[0], sentences[1])
            if merged:
                return merged

        reduced, count = self.merger.reduce_consecutive_endings(
            sentences,
            max_consecutive=2,
            max_chars=self.config.max_compound_chars,
        )
        if count > 0:
            return "".join(reduced)
        return span.target_text

    async def refine_span(
        self,
        span: TargetSpan,
        is_past_locked: bool = True,
        config: Optional[CadenceIntelligentConfig] = None,
    ) -> str:
        """Asynchronously refine a single target span using lightweight LLM."""
        cfg = config or self.config
        if not cfg.enable_llm_refine or self.llm_client is None:
            return self.fallback_refine(span)

        prompt = self.build_prompt(span, is_past_locked=is_past_locked)

        try:
            # タイムアウト付き非同期呼び出し
            async def _call():
                if hasattr(self.llm_client, "generate_text"):
                    res = await self.llm_client.generate_text(
                        model_name=cfg.llm_model_name,
                        prompt=prompt,
                        temp=cfg.llm_temperature,
                    )
                    return getattr(res, "story_content", res) if hasattr(res, "story_content") else str(res)
                elif hasattr(self.llm_client, "ainvoke"):
                    res = await self.llm_client.ainvoke(prompt)
                    return getattr(res, "content", res)
                elif callable(self.llm_client):
                    res = self.llm_client(prompt)
                    if asyncio.iscoroutine(res):
                        res = await res
                    return getattr(res, "content", res) if hasattr(res, "content") else str(res)
                return str(self.llm_client)

            result_text = await asyncio.wait_for(_call(), timeout=cfg.llm_timeout_seconds)
            cleaned = str(result_text).strip().strip('"').strip("'")
            if cleaned:
                return cleaned
        except Exception as e:
            logger.warning(f"Local LLM cadence refinement failed or timed out ({e}). Falling back.")

        return self.fallback_refine(span)

    def refine_span_sync(
        self,
        span: TargetSpan,
        is_past_locked: bool = True,
        config: Optional[CadenceIntelligentConfig] = None,
    ) -> str:
        """Synchronous wrapper for refine_span."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Running loop inside another async context: use fallback to avoid blocking
                return self.fallback_refine(span)
            return loop.run_until_complete(self.refine_span(span, is_past_locked, config))
        except Exception:
            return self.fallback_refine(span)
