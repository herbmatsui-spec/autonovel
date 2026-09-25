"""Main Pipeline Orchestrator for 1-Sheet 24-Panel Manga Generation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from src.services.manga.client import NanoBananaClient
from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import (
    CharacterReference,
    MangaEpisodeInput,
    MangaPipelineResult,
)
from src.services.manga.prompt_generator import MangaPromptGenerator
from src.services.manga.quality_gate import MangaQualityGate
from src.services.manga.typesetter import MangaTypesetter
from src.services.manga.upscaler import MangaUpscaler

logger = logging.getLogger(__name__)


class MangaPipeline:
    """ナノバナナ2ライト（Gemini 3.1 Flash-Lite Image）による

    1話1枚生成（24コマ漫画シート一括生成）＋写植（オプション）パイプライン。
    """

    def __init__(
        self,
        config: Optional[MangaPipelineConfig] = None,
        mock_mode: bool = False,
    ):
        self.config = config or MangaPipelineConfig()
        self.prompt_generator = MangaPromptGenerator()
        self.client = NanoBananaClient(config=self.config, mock_mode=mock_mode)
        self.quality_gate = MangaQualityGate()
        self.upscaler = MangaUpscaler(
            scale_factor=self.config.upscale_factor,
            target_width=self.config.target_upscale_width,
        )
        self.typesetter = MangaTypesetter(config=self.config)

    def run_episode(
        self,
        episode: MangaEpisodeInput,
        character_refs: Optional[List[CharacterReference]] = None,
        enable_typesetting: Optional[bool] = None,
        max_retries: int = 2,
    ) -> MangaPipelineResult:
        """1話分の漫画シートを生成から超解像、オプション写植まで一気通貫で実行する。"""
        # 写植オプションフラグの決定
        do_typeset = (
            enable_typesetting
            if enable_typesetting is not None
            else self.config.enable_typesetting
        )

        # 1. プロンプト生成
        prompt = self.prompt_generator.build_prompt(episode, character_refs)
        negative_prompt = self.prompt_generator.build_negative_prompt()

        api_calls = 0
        raw_sheet_path: Optional[Path] = None
        quality_res = None

        # 2. 1枚生成 ＆ 品質ゲート判定
        for attempt in range(max_retries + 1):
            api_calls += 1
            raw_output_path = (
                self.config.output_base_dir
                / "raw_sheets"
                / f"ep_{episode.episode_number}_attempt_{attempt}.png"
            )
            raw_sheet_path = self.client.generate_sheet(
                prompt=prompt,
                negative_prompt=negative_prompt,
                character_refs=character_refs,
                aspect_ratio=episode.aspect_ratio.value,
                output_path=raw_output_path,
            )

            # 品質評価
            quality_res = self.quality_gate.evaluate(raw_sheet_path)
            if quality_res.is_valid:
                logger.info("Quality gate passed on attempt %d", attempt + 1)
                break
            else:
                logger.warning(
                    "Quality gate failed on attempt %d: %s",
                    attempt + 1,
                    quality_res.reasons,
                )

        assert raw_sheet_path is not None

        # 3. ローカル超解像（無料処理）
        upscaled_path = (
            self.config.output_base_dir
            / "upscaled"
            / f"ep_{episode.episode_number}_upscaled.png"
        )
        upscaled_sheet_path = self.upscaler.upscale(
            raw_sheet_path, output_image_path=upscaled_path
        )

        # 4. 写植（オプション）
        final_output_path = upscaled_sheet_path
        typeset_applied = False

        if do_typeset and episode.dialogues:
            typeset_path = (
                self.config.output_base_dir
                / "finalized"
                / f"ep_{episode.episode_number}_final.png"
            )
            final_output_path = self.typesetter.apply_typesetting(
                image_path=upscaled_sheet_path,
                dialogues=episode.dialogues,
                output_path=typeset_path,
            )
            typeset_applied = True

        # コスト試算（1呼び出しあたり $0.034）
        estimated_cost = api_calls * self.config.cost_per_image_usd

        return MangaPipelineResult(
            episode_number=episode.episode_number,
            raw_sheet_path=raw_sheet_path,
            upscaled_sheet_path=upscaled_sheet_path,
            final_output_path=final_output_path,
            api_calls_count=api_calls,
            estimated_cost_usd=estimated_cost,
            typeset_applied=typeset_applied,
            quality_result=quality_res,
            metadata={
                "title": episode.title,
                "aspect_ratio": episode.aspect_ratio.value,
                "prompt": prompt,
            },
        )
