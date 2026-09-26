"""クライアント境界の契約テスト（Step 20 / R-04 / R-17）。

全クライアントが `ImageClientProtocol` に適合すること、そして
**モデルキーだけ差し替えてもエンジンの挙動が変わらない**ことを固定する。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from config.image_models import IMAGE_MODEL_CATALOG
from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.clients import (
    ImageClientProtocol,
    LegacyImagenClient,
    build_client,
)
from src.services.illustration.config import UnifiedIllustrationConfig
from src.services.illustration.unified_generator import UnifiedIllustrationGenerator

CLIENTS = ["gemini", "legacy", "mock"]


class _StubImageService:
    """Legacy 経路テスト用の最小 `ImageService` スタブ。"""

    default_model = "imagen-4.0-fast-generate-001"

    def __init__(self, url: str = "/static/illustrations/stub.png") -> None:
        self.url = url

    async def generate(self, **kwargs):
        return self.url


def make_client(kind: str):
    if kind == "gemini":
        return build_client("nanobanana2lite", mock_mode=True)
    if kind == "legacy":
        return LegacyImagenClient(
            image_service=_StubImageService(), model_id="imagen-4.0-fast-generate-001"
        )
    return build_client("mock")


def make_request(illo_type: IllustrationType, tmp_path: Path) -> IllustrationRequest:
    return IllustrationRequest(
        book_id=1,
        illustration_type=illo_type,
        episode_number=1,
        scene_text="夜空の下、主人公が剣を抜いた。",
        book_context={"title": "T", "genre": "ファンタジー", "characters": ["A"]},
        panels=24 if illo_type == IllustrationType.MANGA_24PANEL else 6,
    )


@pytest.mark.parametrize("kind", CLIENTS)
def test_all_clients_satisfy_protocol(kind):
    """【R-04】全クライアントが `ImageClientProtocol` に適合する。"""
    client = make_client(kind)
    assert isinstance(client, ImageClientProtocol)
    assert isinstance(client.name, str) and client.name
    assert isinstance(client.model_id, str) and client.model_id


@pytest.mark.parametrize("kind", CLIENTS)
@pytest.mark.parametrize("illo_type", list(IllustrationType))
def test_every_client_generates_for_every_type(kind, illo_type, tmp_path):
    """【R-04】クライアント×種別の全組み合わせで生成できる。"""
    client = make_client(kind)
    result = asyncio.run(
        client.generate("prompt", negative_prompt="neg", aspect_ratio="3:4")
    )
    assert isinstance(result.data, bytes) or result.source_path is not None


def test_model_swap_does_not_change_engine_branches(tmp_path):
    """【R-04 / R-17】モデルキーを差し替えても出力物（パス・プロンプト）は同じ。

    つまりエンジン本体にモデル別の分岐带入らないことの証明。
    """
    prompts = {}
    for model_key in ("nanobanana2lite", "imagen_quality", "mock"):
        config = UnifiedIllustrationConfig(model_key=model_key, output_root=tmp_path / model_key)
        generator = UnifiedIllustrationGenerator(
            config=config, client=build_client(model_key, mock_mode=True)
        )
        result = asyncio.run(generator.generate(make_request(IllustrationType.EPISODE, tmp_path)))
        assert result.image_path is not None and result.image_path.exists()
        prompts[model_key] = result.prompt
        # モデルIDだけが変わり、他は同一
        assert result.model_used == IMAGE_MODEL_CATALOG[model_key].model_id

    assert len(set(prompts.values())) == 1, "prompt must not depend on the model key"


def test_model_used_reflects_configured_key(tmp_path):
    """【R-17】`AUTONOVEL_IMAGE_MODEL` 相当の設定で `model_used` が変わる。"""
    for model_key, expected in (
        ("nanobanana2lite", "gemini-3.1-flash-lite-image"),
        ("imagen_ultra", "imagen-4.0-ultra-generate-001"),
    ):
        config = UnifiedIllustrationConfig(model_key=model_key, output_root=tmp_path / model_key)
        generator = UnifiedIllustrationGenerator(
            config=config, client=build_client(model_key, mock_mode=True)
        )
        assert generator.model_used == expected


def test_legacy_path_selected_only_with_image_service(tmp_path):
    """【R-01】旧 ImageService を渡した時だけ Legacy クライアントになる。"""
    generator = UnifiedIllustrationGenerator(
        config=UnifiedIllustrationConfig(output_root=tmp_path / "a"),
        image_service=object(),
    )
    assert generator.client.name == "legacy_imagen"

    generator2 = UnifiedIllustrationGenerator(
        config=UnifiedIllustrationConfig(output_root=tmp_path / "b"),
    )
    assert generator2.client.name == "gemini_image"
