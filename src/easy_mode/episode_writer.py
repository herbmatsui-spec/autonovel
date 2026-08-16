"""
エピソード執筆モジュール
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.easy_mode.models import RetryConfig

logger = logging.getLogger(__name__)


class EpisodeWriter:
    """エピソード執筆（プロンプト構築・LLM呼び出し・リトライ）"""

    def __init__(
        self,
        engine_llm,
        preset: Dict[str, Any],
        retry_config: Optional[RetryConfig] = None,
    ):
        self.engine_llm = engine_llm
        self.preset = preset
        self.retry_config = retry_config or RetryConfig()
        self._cancelled = False

    async def write(
        self,
        ep_num: int,
        bible: Dict[str, Any],
        plot: Dict[str, Any],
        prev_context: str,
    ) -> str:
        """エピソード執筆"""
        try:
            # プリセットのStyle DNA、フック、官能ルールを注入
            style_dna = self.preset.get("style", {})
            hooks = self.preset.get("hooks", {})
            erotic_rules = self.preset.get("erotic", {})

            # 執筆プロンプト構築・実行
            prompt = self.build_prompt(
                ep_num, bible, plot, prev_context, style_dna, hooks, erotic_rules
            )

            content = await self._generate_with_retry(prompt, {}, f"write_episode_{ep_num}")
            return content
        except Exception as e:
            logger.error(f"Writing failed for ep {ep_num}: {e}")
            return f"[執筆エラー: 第{ep_num}話の生成に失敗しました]"

    def build_prompt(
        self,
        ep_num: int,
        bible: Dict[str, Any],
        plot: Dict[str, Any],
        prev_context: str,
        style_dna: Dict[str, Any],
        hooks: Dict[str, Any],
        erotic_rules: Dict[str, Any],
    ) -> str:
        """執筆プロンプト構築"""
        return f"""
        【第{ep_num}話 執筆指示】

        Bible: {bible}
        プロット: {plot}
        前話文脈: {prev_context}

        Style DNA: {style_dna}
        フック戦略: {hooks}
        官能ルール: {erotic_rules}

        目標文字数: 3000-5000字
        テンション目標: {plot.get("target_tension", 0.5)}
        カタルシス話: {plot.get("is_catharsis", False)}

        以下の制約を厳守せよ：
        1. POV漏れ禁止
        2. ショー・ドン・テル
        3. 各シーン末尾にフック
        4. 官能Lv.{erotic_rules.get("max_intensity_level", 3)}以下
        5. 独自比喩・キャラ声・伏線回収キーワードを保護
        """

    async def _generate_with_retry(
        self, prompt: str, variables: Dict, operation: str = "generate"
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

    def cancel(self):
        """キャンセル"""
        self._cancelled = True