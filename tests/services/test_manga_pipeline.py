"""Unit and integration tests for NanoBanana 2 Lite Manga Pipeline."""
from __future__ import annotations

import tempfile
from pathlib import Path
from PIL import Image

import pytest

from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import (
    AspectRatio,
    CharacterReference,
    MangaEpisodeInput,
    SpeechBubble,
)
from src.services.manga.pipeline import MangaPipeline
from src.services.manga.prompt_generator import MangaPromptGenerator
from src.services.manga.quality_gate import MangaQualityGate
from src.services.manga.typesetter import MangaTypesetter
from src.services.manga.upscaler import MangaUpscaler


def test_prompt_generator_builds_24_panel_silent_prompt():
    """24コマ漫画シート（4x6 grid）および文字なし（サイレント）プロンプトが正しく生成されること。"""
    gen = MangaPromptGenerator()
    ep = MangaEpisodeInput(
        episode_number=1,
        title="目覚めと決意",
        synopsis="主人公が能力に目覚め、ライバルと対峙する。",
        characters=["タロウ", "ハナコ"],
        setting="高校の屋上",
        aspect_ratio=AspectRatio.RATIO_3_4,
    )
    char_refs = [
        CharacterReference(name="タロウ", master_image_path=Path("data/manga/char_ref/taro.png"))
    ]

    prompt = gen.build_prompt(ep, character_refs=char_refs)

    # 必須キーワードの検証
    assert "24 panels" in prompt
    assert "4x6 grid layout" in prompt
    assert "Episode 1" in prompt
    assert "--no text" in prompt
    assert "no speech bubbles" in prompt
    assert "タロウ" in prompt


def test_quality_gate_evaluates_image(tmp_path: Path):
    """品質ゲートが解像度や線画コントラストを正しく評価すること。"""
    gate = MangaQualityGate()

    # 1. 不正（空）ファイル
    empty_file = tmp_path / "empty.png"
    empty_file.touch()
    res_empty = gate.evaluate(empty_file)
    assert not res_empty.is_valid

    # 2. 正常な白黒マンガ風モック画像 (768x1024)
    valid_file = tmp_path / "valid.png"
    img = Image.new("L", (768, 1024), color=255)
    # 線画とベタ黒を描画してコントラストを持たせる
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for y in range(0, 1024, 64):
        draw.line([(0, y), (768, y)], fill=0, width=4)
    for x in range(0, 768, 64):
        draw.line([(x, 0), (x, 1024)], fill=0, width=4)
    draw.rectangle([100, 100, 300, 300], fill=0)
    img.save(valid_file)

    res_valid = gate.evaluate(valid_file)
    assert res_valid.is_valid
    assert res_valid.line_sharpness_score > 0.0


def test_upscaler_magnifies_image(tmp_path: Path):
    """アップスケーラーが画像を4096pxの目標解像度に拡大すること。"""
    upscaler = MangaUpscaler(scale_factor=4, target_width=4096)

    input_img_path = tmp_path / "raw.png"
    img = Image.new("RGB", (768, 1024), color=(255, 255, 255))
    img.save(input_img_path)

    output_img_path = tmp_path / "upscaled.png"
    result_path = upscaler.upscale(input_img_path, output_image_path=output_img_path)

    assert result_path.exists()
    with Image.open(result_path) as upscaled_img:
        w, h = upscaled_img.size
        assert w >= 4096


def test_typesetter_applies_speech_bubbles(tmp_path: Path):
    """写植モジュールがコマ内にフキダシとセリフを描画すること。"""
    config = MangaPipelineConfig()
    typesetter = MangaTypesetter(config=config)

    input_img_path = tmp_path / "sheet.png"
    img = Image.new("RGB", (1024, 1024), color=(240, 240, 240))
    img.save(input_img_path)

    dialogues = [
        SpeechBubble(panel_index=0, text="行くぞ！", rel_x=0.5, rel_y=0.5),
        SpeechBubble(panel_index=5, text="待ちなさい！", rel_x=0.5, rel_y=0.5),
    ]

    output_path = tmp_path / "typeset.png"
    res = typesetter.apply_typesetting(input_img_path, dialogues, output_path=output_path)

    assert res.exists()
    assert res.stat().st_size > 0


def test_pipeline_e2e_mock(tmp_path: Path):
    """パイプライン全体（生成→品質ゲート→超解像→写植）がモックモードでエンドツーエンド動作すること。"""
    config = MangaPipelineConfig(
        output_base_dir=tmp_path / "output",
        target_upscale_width=1024,  # テスト高速化のため
        enable_typesetting=True,
    )
    pipeline = MangaPipeline(config=config, mock_mode=True)

    ep = MangaEpisodeInput(
        episode_number=1,
        title="第1話 テスト",
        synopsis="テストのあらすじ",
        characters=["主人公"],
        dialogues=[
            SpeechBubble(panel_index=0, text="テストセリフ"),
        ],
    )

    result = pipeline.run_episode(ep)

    assert result.episode_number == 1
    assert result.api_calls_count == 1
    assert result.estimated_cost_usd == pytest.approx(0.034, abs=0.001)
    assert result.typeset_applied is True
    assert result.raw_sheet_path.exists()
    assert result.upscaled_sheet_path.exists()
    assert result.final_output_path.exists()
