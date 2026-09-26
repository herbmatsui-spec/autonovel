"""DI コンテナの chroma_client_provider / vector_store の同一性を固定する。"""
from __future__ import annotations

from src.core.container import InfraContainer


def test_vector_store_uses_injected_chroma_client_provider():
    """vector_store は注入された chroma_client_provider を保持すること。"""
    InfraContainer.chroma_client_provider.reset()
    InfraContainer.vector_store.reset()
    store = InfraContainer.vector_store()
    provider = InfraContainer.chroma_client_provider()
    assert store.client_provider is provider


def test_chroma_db_path_is_respected(monkeypatch):
    """ハードコードせず settings.CHROMA_DB_PATH を使うこと。"""
    monkeypatch.setattr("src.backend.config.settings.CHROMA_DB_PATH", "./chroma_db_test_dir")
    InfraContainer.chroma_client_provider.reset()
    provider = InfraContainer.chroma_client_provider()
    assert provider.db_path == "./chroma_db_test_dir"
