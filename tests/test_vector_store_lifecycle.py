
import pytest

from config.container import Container, get_container
from src.services.vector_store import ChromaClientProvider, ChromaVectorStore


@pytest.mark.asyncio
async def test_chroma_provider_lifecycle():
    # DIコンテナからProviderを取得
    container = get_container()
    provider = container.chroma_client_provider()

    # 初回はNoneであること
    assert provider._client is None

    # クライアント取得（Lazy Loading）
    client = provider.get_client()
    assert client is not None
    assert provider._client is not None

    # 複数回呼んでも同じクライアントが返るか
    client2 = provider.get_client()
    assert client is client2

    # close の確認
    provider.close()
    assert provider._client is None

    # 再度取得できるか
    client3 = provider.get_client()
    assert client3 is not None
    assert provider._client is not None

@pytest.mark.asyncio
async def test_vector_store_lazy_loading():
    provider = ChromaClientProvider(db_path="./test_chroma_db")
    store = ChromaVectorStore(client_provider=provider)

    assert provider._client is None
    # 内部的に get_client を呼ぶ操作
    store.get_collection("test_col")
    assert provider._client is not None
