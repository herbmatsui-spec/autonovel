"""Regression tests for NanoBanana 2 Lite 1-Sheet Manga Pipeline.

旧方式（24コマ個別生成・高コスト・長所要時間）への逆戻りを防ぎ、
「1話1枚生成（$0.034/話）」「オプション写植」「サイレントプロンプト」
の仕様が将来にわたって維持されることを保証するリグレッション防止テスト群。
"""
from __future__ import annotations

from pathlib import Path
import pytest

from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import MangaEpisodeInput, SpeechBubble
from src.services.manga.pipeline import MangaPipeline
from src.services.manga.prompt_generator import MangaPromptGenerator


def test_regression_api_call_count_must_be_single_per_episode(tmp_path: Path):
    """【リグレッション防止】1話あたりのAPI呼び出し回数が1回（1枚一括生成）であること。

    もし旧方式（1話24回生成）に逆戻りした場合、即座にFAILする。
    """
    config = MangaPipelineConfig(output_base_dir=tmp_path / "output")
    pipeline = MangaPipeline(config=config, mock_mode=True)

    ep = MangaEpisodeInput(
        episode_number=1,
        title="回数リグレッション検証",
        synopsis="1話のストーリー",
    )
    result = pipeline.run_episode(ep)

    # 1話につき1回のAPIコールであること（24回は厳禁）
    assert result.api_calls_count == 1, (
        f"API call count must be 1 per episode, but was {result.api_calls_count}."
    )


def test_regression_cost_budget_ceiling(tmp_path: Path):
    """【リグレッション防止】1話のコストが $0.05 を超えないこと（目標: $0.034）。

    40話で $2 未満（約$1.36）を維持し、旧方式（40話で$32超）への肥大化を防止する。
    """
    config = MangaPipelineConfig(output_base_dir=tmp_path / "output")
    pipeline = MangaPipeline(config=config, mock_mode=True)

    ep = MangaEpisodeInput(
        episode_number=1,
        title="コスト上限検証",
        synopsis="コスト予算テスト",
    )
    result = pipeline.run_episode(ep)

    # 1話のコスト上限 $0.05
    assert result.estimated_cost_usd <= 0.05, (
        f"Cost per episode exceeded threshold: ${result.estimated_cost_usd} > $0.05"
    )
    # 40話換算でも $2.00 以下
    projected_40_episodes_cost = result.estimated_cost_usd * 40
    assert projected_40_episodes_cost <= 2.00, (
        f"Projected 40 episodes cost ${projected_40_episodes_cost} exceeds $2.00"
    )


def test_regression_optional_typesetting_can_be_disabled(tmp_path: Path):
    """【リグレッション防止】写植は完全なオプションであり、無効時は写植処理がスキップされること。"""
    config = MangaPipelineConfig(
        output_base_dir=tmp_path / "output",
        enable_typesetting=False,  # オプションOFF
    )
    pipeline = MangaPipeline(config=config, mock_mode=True)

    ep = MangaEpisodeInput(
        episode_number=1,
        title="オプション写植検証",
        synopsis="サイレント漫画運用",
        dialogues=[SpeechBubble(panel_index=0, text="セリフがあってもOFFなら無視される")],
    )

    result = pipeline.run_episode(ep, enable_typesetting=False)

    assert result.typeset_applied is False
    # 写植適用されない場合、最終出力パスは超解像画像と同一（無駄な再エンコードなし）
    assert result.final_output_path == result.upscaled_sheet_path


def test_regression_prompt_strictly_prohibits_ai_text():
    """【リグレッション防止】プロンプトが画像生成モデルに対して文字描画を厳格に禁止していること。

    画像生成モデルに文字を描かせると文字化けが発生するため、
    '--no text, no speech bubbles' の禁止句が必須。
    """
    gen = MangaPromptGenerator()
    ep = MangaEpisodeInput(episode_number=1, title="文字禁止検証", synopsis="テスト")
    prompt = gen.build_prompt(ep)

    assert "--no text" in prompt
    assert "no speech bubbles" in prompt
    neg = gen.build_negative_prompt()
    assert "text" in neg
    assert "speech bubbles" in neg


def test_regression_no_file_leak_in_root(tmp_path: Path):
    """【リグレッション防止】パイプライン実行時にルート直下にファイルが一切漏れないこと。"""
    root_before = {p.name for p in Path(".").glob("*")}

    config = MangaPipelineConfig(
        output_base_dir=tmp_path / "output",
        target_upscale_width=512,
    )
    pipeline = MangaPipeline(config=config, mock_mode=True)
    ep = MangaEpisodeInput(episode_number=1, title="漏洩防止", synopsis="テスト")
    pipeline.run_episode(ep)

    root_after = {p.name for p in Path(".").glob("*")}
    new_files_in_root = root_after - root_before
    assert not new_files_in_root, f"New files leaked in root: {new_files_in_root}"
