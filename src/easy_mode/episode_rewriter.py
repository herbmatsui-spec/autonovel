"""
エピソードリライトモジュール（SpiceGuard付き）
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.easy_mode.models import RetryConfig
from src.easy_mode.spice_guard import SpiceElement, create_spice_guard

logger = logging.getLogger(__name__)


class EpisodeRewriter:
    """SpiceGuard付きリライト（マーカー注入・除去・プロンプト構築）"""

    def __init__(
        self,
        engine_llm,
        genre: str,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.engine_llm = engine_llm
        self.genre = genre
        self.retry_config = retry_config or RetryConfig()
        self._spice_guard = create_spice_guard(genre)
        self._cancelled = False

    async def rewrite(
        self, content: str, improvements: List[str], spice_elements: List[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライト"""
        if not improvements:
            return content

        protected_content = self.inject_markers(content, spice_elements)

        prompt = f"""
        以下の小説を改善せよ。ただし、<<<SPICE:...>>> で囲まれた部分は
        『絶対に変更するな。一文字も触るな。そこがこの話の『命』だ。』

        【改善指示】
        {chr(10).join(f"- {imp}" for imp in improvements)}

        【原文】
        {protected_content}

        改善後の本文のみを出力せよ。SPICEマーカーはそのまま残せ。
        """

        try:
            rewritten = await self._generate_with_retry(prompt, {}, "rewrite_episode")
            # SPICEマーカーを除去
            cleaned = re.sub(r"<<<SPICE:[^>]+>>>|<<</SPICE>>>", "", rewritten)
            return cleaned
        except Exception as e:
            logger.error(f"Rewrite failed: {e}")
            return content

    def inject_markers(self, text: str, spice_elements: List[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        # 位置順にソート（後ろから置換）
        sorted_elements = sorted(spice_elements, key=lambda x: x.position, reverse=True)

        result = text
        for elem in sorted_elements:
            pos = elem.position
            length = len(elem.text)
            if pos >= 0 and length > 0:
                marker_id = f"{elem.type}_{pos}"
                before = result[:pos]
                target = result[pos : pos + length]
                after = result[pos + length :]
                result = before + f"<<<SPICE:{marker_id}>>> {target} <<</SPICE>>>" + after

        return result

    def clean_markers(self, text: str) -> str:
        """SPICEマーカーを除去"""
        return re.sub(r"<<<SPICE:[^>]+>>>|<<</SPICE>>>", "", text)

    def build_prompt(
        self, content: str, improvements: List[str], spice_elements: List[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライトプロンプト構築（テスト用公開メソッド）"""
        return self._spice_guard.build_rewrite_prompt(content, improvements, spice_elements)

    def extract_spice(self, text: str) -> List[SpiceElement]:
        """尖り要素の自動抽出"""
        return self._spice_guard.extract_spice(text)

    async def _generate_with_retry(
        self, prompt: str, variables: Dict[str, Any], operation: str = "generate"
    ) -> str:
        """LLM生成をリトライ付きで実行"""
        last_error: Exception = Exception("Unknown error")
        for attempt in range(self.retry_config.max_retries):
            try:
                if self._cancelled:
                    raise RuntimeError("Cancelled")
                result = await self.engine_llm.generate(prompt, variables)
                if result and result.strip():
                    return result
                last_error = Exception("Empty response from LLM")
            except Exception as e:
                if self._cancelled:
                    raise
                last_error = e
                logger.warning(
                    f"{operation} attempt {attempt + 1}/{self.retry_config.max_retries} failed: {e}"
                )
                if attempt < self.retry_config.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(self.retry_config.delay_for_attempt(attempt))

        logger.error(f"{operation} failed after {self.retry_config.max_retries} attempts: {last_error}")
        raise last_error

    def cancel(self) -> None:
        """キャンセル"""
        self._cancelled = True
