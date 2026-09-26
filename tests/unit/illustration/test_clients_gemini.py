"""画像生成クライアントのテスト（Step 19: Gemini / Legacy / Mock）。"""

from __future__ import annotations

import pytest

from config.image_models import IMAGE_MODEL_CATALOG
from src.services.illustration.clients import (
    GeneratedImage,
    GeminiImageClient,
    LegacyImagenClient,
    MockImageClient,
    PermanentClientError,
    TransientClientError,
    build_client,
)

ALL_TYPES = ["cover", "episode", "character", "yonkoma", "manga_24panel"]


class _FakeModels:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def generate_images(self, model, prompt, config):
        self.calls.append({"model": model, "prompt": prompt, "config": config})
        image = type("Img", (), {"image": type("Inner", (), {"image_bytes": self.payload})()})()
        return type("Resp", (), {"generated_images": [image]})()


class _FakeClient:
    def __init__(self, payload: bytes = b"\x89PNG\r\n\x1a\nFAKE") -> None:
        self.models = _FakeModels(payload)


def test_mock_client_returns_png_bytes():
    """mock モードでも PNG バイト列が返る（パイプラインが成立する）。"""
    import asyncio

    client = GeminiImageClient(mock_mode=True)
    result = asyncio.run(client.generate("prompt"))
    assert isinstance(result, GeneratedImage)
    assert result.data.startswith(b"\x89PNG")
    assert result.meta["mock"] is True


def test_gemini_client_uses_configured_model_id():
    """クライアントはカタログのモデルIDをそのまま使う。"""
    import asyncio

    spec = IMAGE_MODEL_CATALOG["nanobanana2lite"]
    fake = _FakeClient()
    client = GeminiImageClient(model_id=spec.model_id, mock_mode=False, client=fake)
    result = asyncio.run(client.generate("hello", aspect_ratio="2:3"))
    assert fake.models.calls[0]["model"] == spec.model_id
    assert result.meta["model_id"] == spec.model_id


def test_gemini_client_without_key_falls_back_to_mock(monkeypatch):
    """APIキー無しでも例外で落ちず mock へ退避する（CI で安全）。"""
    import asyncio

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    monkeypatch.delenv("NANOBANANA_API_KEY", raising=False)
    client = GeminiImageClient(mock_mode=False, api_key="")
    result = asyncio.run(client.generate("hello"))
    assert result.meta["mock"] is True


def test_gemini_client_classifies_permanent_errors():
    """恒久エラーはリトライ不要として分類される。"""
    error = GeminiImageClient._classify(RuntimeError("400 INVALID_ARGUMENT: bad prompt"))
    assert isinstance(error, PermanentClientError)

    error = GeminiImageClient._classify(RuntimeError("503 overloaded, try again"))
    assert isinstance(error, TransientClientError)
    assert not isinstance(error, PermanentClientError)


def test_gemini_client_warns_on_unsupported_reference_images(tmp_path):
    """SDK が参照画像に非対応でも黙って落ちない（警告して継続）。"""
    import asyncio

    from PIL import Image

    ref = tmp_path / "ref.png"
    Image.new("RGB", (8, 8), color=(128, 128, 128)).save(ref)

    client = GeminiImageClient(mock_mode=False, client=_FakeClient())
    result = asyncio.run(client.generate("hello", reference_images=(str(ref),)))
    assert result.data  # 生成自体は成功
    # 存在しない参照画像は無視される
    result2 = asyncio.run(client.generate("hello", reference_images=("missing.png",)))
    assert result2.data


class _StubImageService:
    default_model = "imagen-4.0-ultra-generate-001"

    def __init__(self, url: str = "/static/illustrations/x.png") -> None:
        self.url = url
        self.calls: list[dict] = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.url


def test_legacy_client_delegates_to_image_service(tmp_path, monkeypatch):
    """Legacy クライアントは旧 ImageService へ委譲し URL を meta へ返す。"""
    import asyncio

    monkeypatch.chdir(tmp_path)
    service = _StubImageService()
    client = LegacyImagenClient(image_service=service)
    result = asyncio.run(client.generate("prompt", negative_prompt="bad"))
    assert result.meta["url"] == service.url
    assert service.calls[0]["negative_prompt"] == "bad"
    assert service.calls[0]["model"] == "imagen-4.0-ultra-generate-001"


def test_legacy_client_classifies_errors():
    import asyncio

    class _Failing:
        default_model = "imagen-4.0-fast-generate-001"

        async def generate(self, **kwargs):
            raise RuntimeError("invalid argument: unsupported aspect ratio")

    client = LegacyImagenClient(image_service=_Failing())
    with pytest.raises(PermanentClientError):
        asyncio.run(client.generate("prompt"))


def test_mock_client_records_calls():
    import asyncio

    client = MockImageClient()
    asyncio.run(client.generate("p1", aspect_ratio="2:3"))
    asyncio.run(client.generate("p2"))
    assert [c["prompt"] for c in client.calls] == ["p1", "p2"]
    assert client.calls[0]["aspect_ratio"] == "2:3"


@pytest.mark.parametrize("model_key", ["nanobanana2lite", "imagen_fast", "imagen_quality", "imagen_ultra", "mock"])
def test_factory_builds_client_for_every_catalog_entry(model_key):
    """カタログの全モデルキーでクライアントを組み立てられる。"""
    client = build_client(model_key, mock_mode=True)
    spec = IMAGE_MODEL_CATALOG[model_key]
    assert client.name in ("gemini_image", "legacy_imagen", "mock")
    assert client.model_id == spec.model_id
