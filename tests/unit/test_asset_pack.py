"""src.easy_mode.phase3.asset_pack の単体テスト。"""
from __future__ import annotations

import json
import zipfile

from src.easy_mode.phase3.asset_pack import AssetPackGenerator, AssetPackMetadata
from src.easy_mode import EpisodeResult, SeriesResult
from src.easy_mode.spice_guard import SpiceElement


def _make_series() -> SeriesResult:
    content = "テスト本文\n\n主人公は森へ行った。\n"
    return SeriesResult(
        genre="ハイファンタジー (R15)",
        title="テストシリーズ",
        concept="テスト",
        total_episodes=1,
        episodes=[
            EpisodeResult(
                episode_num=1,
                title="テスト話",
                content=content,
                word_count=len(content),
                audit_score=80.0,
                audit_passed=True,
                rewrite_count=0,
                spice_elements=[SpiceElement(type="unique_metaphor", text="", position=0, priority="low")],
                metadata={},
            )
        ],
        bible={},
        plot_outline=[],
        metadata={},
    )


def test_asset_pack_metadata_to_dict():
    meta = AssetPackMetadata(
        pack_id="test-pack",
        title="テストパック",
        genre="ハイファンタジー (R15)",
        episode_count=1,
        total_words=100,
    )
    d = meta.to_dict()
    assert d["pack_id"] == "test-pack"
    assert d["title"] == "テストパック"
    assert d["version"] == "1.0.0"
    assert "created_at" in d


def test_asset_pack_generator_creates_zip(tmp_path):
    series = _make_series()
    preset = {"characters": {"archetypes": {}}, "erotic": {}}
    gen = AssetPackGenerator("ハイファンタジー (R15)", preset)
    output_dir = tmp_path / "pack"
    zip_path = gen.generate_pack(series, output_dir=output_dir)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    # 少なくともメタデータファイルとシリーズデータが含まれる
    assert "05_metadata/pack_metadata.json" in names
    assert "01_original_novel/series_complete.json" in names
    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest = json.loads(zf.read("05_metadata/pack_metadata.json"))
    assert manifest["title"] == "テストシリーズ"
