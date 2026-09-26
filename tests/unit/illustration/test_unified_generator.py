"""統合エンジンのユニットテスト（Step 19 / R-05 / R-07 / R-18）。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.clients import (
    MockImageClient,
    PermanentClientError,
    TransientClientError,
    build_client,
)
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.quality_gate import QualityGate
from src.services.illustration.unified_generator import UnifiedIllustrationGenerator

ALL_TYPES = list(IllustrationType)


def make_config(tmp_path: Path, **kwargs) -> UnifiedIllustrationConfig:
    params = {"output_root": tmp_path / "out", "mock_mode": True, "max_retries": 0}
    params.update(kwargs)
    return UnifiedIllustrationConfig(**params)


def make_request(illo_type: IllustrationType, book_id: int = 1) -> IllustrationRequest:
    return IllustrationRequest(
        book_id=book_id,
        illustration_type=illo_type,
        episode_number=2,
        scene_text="夜空の下、主人公が剣を抜いた。光が走る。",
        book_context={"title": "T", "genre": "ファンタジー", "characters": ["A"]},
        panels=24 if illo_type == IllustrationType.MANGA_24PANEL else 6,
    )


def make_generator(tmp_path: Path, client=None, **config_kwargs) -> UnifiedIllustrationGenerator:
    """生成器を作る。クライアント未指定ならカタログ準拠の mock を使う。"""
    return UnifiedIllustrationGenerator(
        config=make_config(tmp_path, **config_kwargs),
        client=client or build_client("nanobanana2lite", mock_mode=True),
    )


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_generate_writes_book_scoped_file(illo_type, tmp_path):
    """【R-07】出力は `{output_root}/{book_id}/` 配下に作られる。"""
    generator = make_generator(tmp_path)
    result = asyncio.run(generator.generate(make_request(illo_type, book_id=42)))
    assert result.image_path is not None
    assert result.image_path.parent == tmp_path / "out" / "42"
    assert result.image_path.exists()
    assert illo_type.value in result.image_path.name


@pytest.mark.parametrize("illo_type", ALL_TYPES)
def test_generate_returns_populated_result(illo_type, tmp_path):
    """【R-01】全種別が同一モデル・非空プロンプトで結果を返す。"""
    generator = make_generator(tmp_path)
    result = asyncio.run(generator.generate(make_request(illo_type)))
    assert result.model_used == "gemini-3.1-flash-lite-image"
    assert result.prompt
    assert result.image_url  # UI 互換のため必ず埋まる
    assert result.estimated_cost_usd == pytest.approx(0.034)


def test_quality_gate_failure_does_not_fail_generation(tmp_path):
    """【R-05】品質ゲートNGでも生成は成功扱い（過剰リトライ・コスト爆を防ぐ）。"""
    generator = make_generator(tmp_path, enable_quality_gate=True)
    result = asyncio.run(generator.generate(make_request(IllustrationType.EPISODE)))
    assert result.image_path.exists()
    assert result.quality is not None
    # mock の 1x1 PNG は解像度不足で不合格になるが、例外は出ていない
    assert result.quality["is_valid"] is False
    assert result.quality["reasons"]


def test_quality_gate_can_be_disabled(tmp_path):
    """【R-05】`enable_quality_gate=False` で品質ゲートはスキップされる。"""
    generator = make_generator(tmp_path, enable_quality_gate=False)
    result = asyncio.run(generator.generate(make_request(IllustrationType.EPISODE)))
    assert result.quality is None


def test_upscale_optional(tmp_path):
    """超解像は任意。OFFなら最終パスが生出力と同じ。"""
    off = make_generator(tmp_path, enable_upscale=False)
    assert off.upscaler is not None
    result = asyncio.run(off.generate(make_request(IllustrationType.EPISODE)))
    assert result.upscaled_path is None


def test_batch_generation_continues_on_failure(tmp_path):
    """【R-05】1件失敗してもバッチ全体は止まらない（failed は None）。"""
    class _FlakyClient(MockImageClient):
        async def generate(self, prompt, **kwargs):
            if "cover" in prompt.lower():
                raise PermanentClientError("boom")
            return await super().generate(prompt, **kwargs)

    generator = make_generator(tmp_path, client=_FlakyClient())
    requests = [make_request(IllustrationType.EPISODE), make_request(IllustrationType.COVER)]
    results = asyncio.run(generator.generate_batch(requests))
    assert len(results) == 2
    assert results[0] is not None
    assert results[1] is None


def test_transient_error_is_retried(tmp_path):
    """一時エラーは設定回数だけリトライされる。"""
    attempts = {"n": 0}

    class _RetryingClient(MockImageClient):
        async def generate(self, prompt, **kwargs):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise TransientClientError("temporary")
            return await super().generate(prompt, **kwargs)

    generator = make_generator(
        tmp_path, client=_RetryingClient(), max_retries=3, retry_backoff_sec=0.0
    )
    result = asyncio.run(generator.generate(make_request(IllustrationType.EPISODE)))
    assert attempts["n"] == 3
    assert result.image_path.exists()


def test_permanent_error_not_retried(tmp_path):
    """恒久エラーは1回で打ち切る（無駄な課金を避ける）。"""
    attempts = {"n": 0}

    class _BrokenClient(MockImageClient):
        async def generate(self, prompt, **kwargs):
            attempts["n"] += 1
            raise PermanentClientError("invalid")

    generator = make_generator(tmp_path, client=_BrokenClient(), max_retries=3, retry_backoff_sec=0.0)
    with pytest.raises(PermanentClientError):
        asyncio.run(generator.generate(make_request(IllustrationType.EPISODE)))
    assert attempts["n"] == 1


def test_repeated_generation_has_no_collision(tmp_path):
    """【R-18】同一入力を2回生成してもファイル名が衝突しない。"""
    generator = make_generator(tmp_path)
    request = make_request(IllustrationType.EPISODE)
    first = asyncio.run(generator.generate(request))
    second = asyncio.run(generator.generate(request))
    assert first.image_path != second.image_path
    assert first.image_path.exists() and second.image_path.exists()


def test_no_file_leak_in_root(tmp_path, monkeypatch):
    """【R-07】リポジトリルートへファイルを漏らさない。"""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    before = {p.name for p in workdir.iterdir()}

    generator = make_generator(workdir, output_root=Path("static/illustrations"))
    asyncio.run(generator.generate(make_request(IllustrationType.EPISODE)))

    after = {p.name for p in workdir.iterdir()}
    assert after - before == {"static"}


def test_cost_estimates_come_from_catalog(tmp_path):
    """コスト試算はカタログ準拠（1枚 $0.034 / 24枚 ≈ $0.82）。"""
    generator = make_generator(tmp_path)
    request = make_request(IllustrationType.MANGA_24PANEL)
    assert generator.estimate_cost(request) == pytest.approx(0.034)
    assert generator.estimate_cost_batch([request] * 24) == pytest.approx(0.816)


def test_quality_gate_degrades_without_pillow(tmp_path, monkeypatch):
    """【R-06】Pillow 不在でも品質ゲートは縮退し、生成は成功する。"""
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name.startswith("PIL"):
            raise ImportError("No module named 'PIL'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    gate = QualityGate()
    empty = tmp_path / "x.png"
    empty.write_bytes(b"not-a-png")
    evaluation = gate.evaluate(empty)
    # Pillow 不在は「不合格」ではなく「スキップ」（生成を止めない）
    assert evaluation.skipped is True
    assert evaluation.is_valid is True

    generator = make_generator(tmp_path, enable_quality_gate=True)
    result = asyncio.run(generator.generate(make_request(IllustrationType.EPISODE)))
    assert result.image_path.exists()


def test_empty_payload_still_produces_file(tmp_path):
    """画像データが空でも後段が成立する 1x1 PNG を置く。"""
    class _EmptyClient(MockImageClient):
        async def generate(self, prompt, **kwargs):
            from src.services.illustration.clients.base import GeneratedImage

            return GeneratedImage(data=b"", meta={"model_id": self.model_id})

    generator = make_generator(tmp_path, client=_EmptyClient())
    result = asyncio.run(generator.generate(make_request(IllustrationType.COVER)))
    assert result.image_path.exists()
    assert result.image_path.stat().st_size > 0
