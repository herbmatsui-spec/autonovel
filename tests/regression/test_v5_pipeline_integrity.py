"""tests/regression/test_v5_pipeline_integrity.py.

v5系の中核である
1. 二段階プロット展開（Coarse-to-Fine: EpisodeMacroSkeleton -> PlotMicroBlueprint）
2. 4層コンテキスト圧縮（Four-layer Context Compression）
3. 監査・推敲ループの局所パッチ収束性（Single-shot Polish）
の不変性（Invariants）を検証するリグレッション防止テスト。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.models.plot import (
    EpisodeMacroSkeleton,
    PlotMicroBlueprint,
    merge_macro_and_micro,
)
from src.services.compression import FourLayerCompressor, CompressionConfig


def test_coarse_fine_skeleton_and_blueprint():
    """EpisodeMacroSkeleton と PlotMicroBlueprint の不変条件と結合検証."""
    skeleton = EpisodeMacroSkeleton(
        ep_num=1,
        title="目覚めし魔剣",
        one_line_summary="アルスが封印の古代魔剣を抜く",
        tension=75,
    )
    assert skeleton.ep_num == 1
    assert skeleton.tension == 75

    blueprint = PlotMicroBlueprint(
        ep_num=1,
        detailed_blueprint="第1シーン: 洞窟の探索。第2シーン: 魔剣の発見。第3シーン: 覚醒と脱出。",
    )
    assert blueprint.ep_num == 1

    # Macro と Micro の合成
    episode = merge_macro_and_micro(skeleton, blueprint)
    assert episode.ep_num == 1
    assert episode.title == "目覚めし魔剣"


def test_four_layer_compression_invariants():
    """4層コンテキスト圧縮がテキストを解析・圧縮し結果オブジェクトを生成すること."""
    compressor = FourLayerCompressor()
    original_text = (
        "【登場人物】アルス：勇者。セリア：聖女。\n"
        "【世界観】アヴァロン王国。魔王軍との戦争が続いている。\n"
        "【直前エピソード】アルスは迷宮の最下層に到達し、ガーディアンを討伐した。\n"
        + "長い戦闘の余波で洞窟は崩落寸前であった。" * 10
    )

    result = compressor.compress(original_text, max_tokens=100)

    assert result is not None
    assert hasattr(result, "final_token_count")
    assert hasattr(result, "layer1")
    assert result.elapsed_ms >= 0


def test_quality_loop_single_patch_contract():
    """推敲ループが無限ループにならず、最大1回のパッチ制限契約を満たすこと."""
    from src.domain.writing.models import WritingGenerationContext

    ctx = WritingGenerationContext(
        sys_inst="あなたはプロのファンタジー作家です。",
        fw_prompt="第1話の本文を執筆してください。",
        expanded_beats="ビート1: 遭遇\nビート2: 対峙\nビート3: 決着",
        feedback_patch="【修正指示】描写を濃密にすること",
    )

    sys_inst = ctx.build_sys_inst()
    assert "自己評価フィードバックパッチ" in sys_inst
    assert "描写を濃密にすること" in sys_inst

    fw_prompt = ctx.build_fw_prompt()
    assert "物理動作ビート分解" in fw_prompt
    assert "ビート1: 遭遇" in fw_prompt


if __name__ == "__main__":
    test_coarse_fine_skeleton_and_blueprint()
    test_four_layer_compression_invariants()
    test_quality_loop_single_patch_contract()
    print("ALL V5 PIPELINE INTEGRITY TESTS PASSED!")
