"""外部API・整形コピー・EPUB・コストガードの総合結合テスト (v5.0 Step 24).

Zero-Cost Infra & Pure Creative Pipelineの全要素（画像/音声の外部従量アダプタ、
投稿サイト整形コピー、純Python商用EPUB 3生成、トークン/コストガードレール）が
完全に連動して動作することを検証する。
"""
from __future__ import annotations

import pytest
from src.services.illustration.factory import get_image_adapter
from src.services.illustration.adapters.base import ImagePromptRequest
from src.services.audio.factory import get_tts_adapter
from src.services.audio.adapters.base import AudioTtsRequest
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter
from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder
from src.services.cost_guard.budget_calculator import BudgetCalculator
from src.services.cost_guard.token_circuit_breaker import TokenCircuitBreaker


@pytest.mark.asyncio
async def test_zero_cost_pipeline_integration():
    # 1. 外部従量モック画像アダプタ
    img_adapter = get_image_adapter("mock")
    img_res = await img_adapter.generate_image(ImagePromptRequest(prompt="test"))
    assert img_res.cost_usd == 0.0
    assert img_res.provider == "mock"
    assert len(img_res.image_bytes) > 0

    # 2. 外部従量モック音声アダプタ
    tts_adapter = get_tts_adapter("mock")
    tts_res = await tts_adapter.synthesize(AudioTtsRequest(text="セリフ"))
    assert tts_res.cost_usd == 0.0
    assert tts_res.provider == "mock"
    assert len(tts_res.audio_bytes) > 0

    # 3. 投稿サイト整形（なろう、カクヨム）
    formatted_narou = PlatformCopyFormatter.format_for_platform(
        "題名",
        "「こんにちは」\n|転生《てんせい》した。",
        platform="narou",
    )
    assert formatted_narou.platform == "narou"
    assert "|転生《てんせい》" in formatted_narou.body

    formatted_kakuyomu = PlatformCopyFormatter.format_for_platform(
        "題名",
        "|転生《てんせい》した。",
        platform="kakuyomu",
    )
    assert formatted_kakuyomu.platform == "kakuyomu"

    # 4. 商用EPUB 3生成（純Python/KDP準拠縦書き）
    epub_builder = PureCommercialEpubBuilder()
    epub_bytes = epub_builder.build_epub(
        "小説タイトル",
        "作者名",
        [{"title": "第1話", "body": "「行くぞ！」\n|勇者《ゆうしゃ》が叫んだ。"}],
    )
    assert len(epub_bytes) > 200

    # 5. コスト計算 & サーキットブレーカー
    cost = BudgetCalculator.calculate_cost("gemini-2.5-flash", 8000, 2500)
    breaker = TokenCircuitBreaker(max_tokens_per_episode=30000, max_cost_jpy_per_episode=10.0)
    breaker.record_usage(cost.prompt_tokens + cost.completion_tokens, cost.cost_jpy)
    assert breaker.accumulated_tokens == 10500
    assert breaker.accumulated_cost_jpy < 10.0
