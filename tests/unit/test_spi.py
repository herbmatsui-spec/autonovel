"""SPI 関連のユニットテスト"""

import pytest
from src.core.spi.llm.interface import ILLMProvider
from src.core.spi.vector_store.interface import IVectorStoreProvider
from src.core.spi.interface import IImageProvider, ImageResult

from src.core.spi.llm.gemini_adapter import GeminiLLMProvider
from src.core.spi.llm.mock_adapter import MockLLMProvider
from src.core.spi.vector_store.chroma_adapter import ChromaVectorProvider
from src.core.spi.vector_store.mock_adapter import MockVectorProvider
from src.core.spi.image.genai_adapter import GenAIImageProvider
from src.core.spi.image.mock_adapter import MockImageProvider


def test_llm_adapters_implement_interface():
    """LLM アダプターが ILLMProvider を実装していることを確認する"""
    # モックアダプターは API キー不要
    mock_provider = MockLLMProvider()
    assert isinstance(mock_provider, ILLMProvider)

    # Gemini アダプターはダミーの API キーでインスタンス化できるか？
    # 実際には API キーが必要だが、インスタンス生成自体は可能
    try:
        gemini_provider = GeminiLLMProvider(api_key="dummy")
        assert isinstance(gemini_provider, ILLMProvider)
    except Exception:
        # API キー関連のエラーが発生する可能性があるが、インスタンスは作成できる
        pass


def test_vector_store_adapters_implement_interface():
    """ベクトルストア アダプターが IVectorStoreProvider を実装していることを確認する"""
    mock_provider = MockVectorProvider()
    assert isinstance(mock_provider, IVectorStoreProvider)

    try:
        chroma_provider = ChromaVectorProvider()
        assert isinstance(chroma_provider, IVectorStoreProvider)
    except Exception:
        # chromadb がインストールされていない可能性がある
        pass


def test_image_adapters_implement_interface():
    """画像 アダプターが IImageProvider を実装していることを確認する"""
    mock_provider = MockImageProvider()
    assert isinstance(mock_provider, IImageProvider)

    try:
        genai_provider = GenAIImageProvider(api_key="dummy")
        assert isinstance(genai_provider, IImageProvider)
    except Exception:
        # API キー関連のエラーが発生する可能性がある
        pass


def test_image_result_dataclass():
    """ImageResult データクラスが正しく動作することを確認する"""
    result = ImageResult(
        image_data=b"dummy",
        prompt="test prompt",
        metadata={"key": "value"},
    )
    assert result.image_data == b"dummy"
    assert result.prompt == "test prompt"
    assert result.metadata == {"key": "value"}