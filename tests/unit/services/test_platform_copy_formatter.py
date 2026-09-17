"""投稿サイト別（なろう・カクヨム・アルファポリス）整形コピーエンジンの単体テスト (v5.0 Step 13)."""
import pytest

from src.services.formatters.platform_copy_formatter import (
    FormattedChapterPayload,
    PlatformCopyFormatter,
)


def test_narou_formatting():
    res = PlatformCopyFormatter.format_for_platform(
        title="第1章 旅立ち",
        body="「行くぞ」\n旅人は言った。\n\n\n\n|真紅《しんく》の瞳が輝く。",
        foreword="前書きです。",
        afterword="後書きです。",
        platform="narou",
    )
    assert res.platform == "narou"
    assert res.title == "第1章 旅立ち"
    assert res.foreword == "前書きです。"
    assert res.afterword == "後書きです。"
    assert "「行くぞ」" in res.body
    assert "　旅人は言った。" in res.body
    assert "|真紅《しんく》" in res.body
    # 連続空行が2行以内に抑制されていること
    assert "\n\n\n" not in res.body
    assert res.total_characters > 0


def test_kakuyomu_formatting():
    res = PlatformCopyFormatter.format_for_platform(
        title="第2章 遭遇",
        body="森の奥で、｜魔導書《グリモワール》を発見した。",
        platform="kakuyomu",
    )
    assert res.platform == "kakuyomu"
    assert "|魔導書《グリモワール》" in res.body


def test_alphapolis_formatting():
    res = PlatformCopyFormatter.format_for_platform(
        title="第3章 決着",
        body="|勇者《ゆうしゃ》よ、立ち上がれ！\n「はい！」",
        platform="alphapolis",
    )
    assert res.platform == "alphapolis"
    assert "#勇者__ゆうしゃ#" in res.body
    assert "「はい！」" in res.body


def test_empty_or_whitespace_handling():
    res = PlatformCopyFormatter.format_for_platform(
        title="",
        body="",
        platform="narou",
    )
    assert res.title == ""
    assert res.body == ""
    assert res.total_characters == 0


@pytest.mark.asyncio
async def test_platform_export_router():
    from src.backend.routers.platform_export import (
        CopyFormatRequest,
        format_chapter_for_copy,
    )

    req = CopyFormatRequest(
        title="テスト話",
        body="「こんにちは」\n少女は笑った。",
        platform="alphapolis",
    )
    resp = await format_chapter_for_copy(req)
    assert resp.platform == "alphapolis"
    assert resp.title == "テスト話"
    assert "「こんにちは」" in resp.body
    assert "　少女は笑った。" in resp.body
