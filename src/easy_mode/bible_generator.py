"""
Bible生成モジュール
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.core.exceptions import BibleGenerationError
from src.easy_mode.models import RetryConfig

logger = logging.getLogger(__name__)


class BibleGenerator:
    """Bible自動生成（プリセット注入・パース・フォールバック）"""

    def __init__(
        self,
        preset: Dict[str, Any],
        engine_llm,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.preset = preset
        self.engine_llm = engine_llm
        self.retry_config = retry_config or RetryConfig()
        self._cancelled = False

    async def generate(self, target_episodes: int) -> Dict[str, Any]:
        """Bible生成メインエントリ"""
        # プロンプトテンプレートを直接使用（モジュールパス問題回避）
        bible_template = self.preset.get("bible", "")

        # プリセットからデフォルト変数を取得
        preset_vars = self._get_preset_defaults()

        # エピソード構造設定をプリセットから取得（デフォルト値付き）
        episode_structure = self.preset.get("episode_structure", {}).get("episode_structure", {})

        # 変数をマージ
        variables = {
            "world_rules_json": "{}",
            "concept": preset_vars.get("concept", "デフォルトコンセプト"),
            "protagonist_name": preset_vars.get("protagonist_name", "主人公"),
            "betrayal_type": preset_vars.get("betrayal_type", "追放"),
            "catharsis_target": preset_vars.get("catharsis_target", "元パーティ"),
            "cheat_ability": preset_vars.get("cheat_ability", "全スキル習得"),
            "schema_json": "{}",
            "humiliation_ep": str(episode_structure.get("humiliation_ep", 2)),
            "trigger_ep": str(episode_structure.get("trigger_ep", 3)),
            "musou_start_ep": str(episode_structure.get("musou_start_ep", 4)),
            "final_ep": str(episode_structure.get("final_ep", 8)),
            "tension_threshold": str(episode_structure.get("tension_threshold", 75)),
        }
        variables.update(preset_vars)

        # LLMで生成（リトライ付き）
        try:
            bible_text = await self._generate_with_retry(
                bible_template, variables, "bible_generation"
            )
            # パースして辞書化
            bible = self.parse(bible_text)
        except Exception as e:
            if self._cancelled:
                raise
            logger.warning(f"Bible generation failed, using fallback: {e}", extra={"error_code": "BIBLE_GENERATION_ERROR"})
            # フォールバックを返す（例外を投げずに継続）
            bible = self.fallback(variables)
            # メタデータに失敗情報を記録
            bible["generation_failed"] = True
            bible["failure_reason"] = str(e)

        return bible

    def parse(self, text: str) -> Dict[str, Any]:
        """Bibleテキストをパース"""
        try:
            return json.loads(text)
        except Exception:
            # フォールバック：テキストをそのまま格納
            return {"raw": text, "parsed": False}

    def fallback(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Bible生成失敗時のフォールバック"""
        return {
            "world": variables.get("world_rules_json", "{}"),
            "concept": variables.get("concept", ""),
            "protagonist": variables.get("protagonist_name", "主人公"),
            "cheat_ability": variables.get("cheat_ability", ""),
            "catharsis_target": variables.get("catharsis_target", ""),
            "fallback": True,
        }

    def _get_preset_defaults(self) -> Dict[str, Any]:
        """プリセットからデフォルト変数を抽出"""
        defaults = {}

        chars = self.preset.get("characters", {})
        if "archetypes" in chars:
            proto = chars["archetypes"].get("protagonist") or chars["archetypes"].get("dm")
            if proto:
                defaults["protagonist_name"] = proto.get("name_pattern", "主人公").split("（")[0]

        titles = self.preset.get("titles", {})
        if titles.get("title_templates"):
            defaults["title_template"] = titles["title_templates"][0]

        marketing = self.preset.get("marketing", {})
        if marketing.get("synopsis_structure"):
            defaults["concept"] = marketing["synopsis_structure"].get("hook", "")

        # episode_structure からデフォルト値を抽出
        episode_structure = self.preset.get("episode_structure", {}).get("episode_structure", {})
        if episode_structure:
            defaults["humiliation_ep"] = episode_structure.get("humiliation_ep", 2)
            defaults["trigger_ep"] = episode_structure.get("trigger_ep", 3)
            defaults["musou_start_ep"] = episode_structure.get("musou_start_ep", 4)
            defaults["final_ep"] = episode_structure.get("final_ep", 8)
            defaults["tension_threshold"] = episode_structure.get("tension_threshold", 75)
            # catharsis_spikes と density_by_phase も利用可能に
            defaults["catharsis_spikes"] = self.preset.get("episode_structure", {}).get("catharsis_spikes", [0.25, 0.5, 0.75, 1.0])
            defaults["density_by_phase"] = self.preset.get("episode_structure", {}).get("density_by_phase", {})

        return defaults

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