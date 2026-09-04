"""Unit tests for src/services/vector_store.py - Vector store service."""
import pytest
from unittest.mock import MagicMock, patch

# Test ChromaClientProvider initialization
def test_chroma_client_provider_init_defaults():
    """Test ChromaClientProvider initialization with default parameters."""
    from src.services.vector_store import ChromaClientProvider
    
    provider = ChromaClientProvider()
    assert provider.db_path == "./chroma_db"
    assert provider.host is None
    assert provider.port is None
    assert provider._client is None

def test_chroma_client_provider_init_custom_params():
    """Test ChromaClientProvider initialization with custom parameters."""
    from src.services.vector_store import ChromaClientProvider
    
    provider = ChromaClientProvider(
        db_path="/custom/path",
        host="localhost",
        port=8000
    )
    assert provider.db_path == "/custom/path"
    assert provider.host == "localhost"
    assert provider.port == 8000
    assert provider._client is None

# Test ChromaClientProvider.get_client() method
def test_chroma_client_provider_get_client_success():
    """Test successful client retrieval from ChromaClientProvider."""
    from src.services.vector_store import ChromaClientProvider, HAS_CHROMA
    
    if not HAS_CHROMA:
        pytest.skip("ChromaDB not available")
        
    provider = ChromaClientProvider()
    
    # Mock the chromadb module and PersistentClient
    with patch('src.services.vector_store.chromadb') as mock_chroma:
        mock_client = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        
        client = provider.get_client()
        
        assert client == mock_client
        mock_chroma.PersistentClient.assert_called_once_with(path="./chroma_db")
        assert provider._client == mock_client

def test_chroma_client_provider_get_client_http():
    """Test HTTP client retrieval from ChromaClientProvider."""
    from src.services.vector_store import ChromaClientProvider, HAS_CHROMA
    
    if not HAS_CHROMA:
        pytest.skip("ChromaDB not available")
        
    provider = ChromaClientProvider(host="remote-host", port=9000)
    
    # Mock the chromadb module and HttpClient
    with patch('src.services.vector_store.chromadb') as mock_chroma:
        mock_client = MagicMock()
        mock_chroma.HttpClient.return_value = mock_client
        
        client = provider.get_client()
        
        assert client == mock_client
        mock_chroma.HttpClient.assert_called_once_with(host="remote-host", port=9000)
        assert provider._client == mock_client

def test_chroma_client_provider_get_client_failure_retry():
    """Test client retrieval with connection failure and retry logic."""
    from src.services.vector_store import ChromaClientProvider, HAS_CHROMA
    import time
    
    if not HAS_CHROMA:
        pytest.skip("ChromaDB not available")
        
    provider = ChromaClientProvider()
    
    # Mock the chromadb module to fail on first attempt, succeed on second
    with patch('src.services.vector_store.chromadb') as mock_chroma, \
         patch('time.sleep') as mock_sleep:
        
        mock_chroma.PersistentClient.side_effect = [
            Exception("Connection failed"),
            MagicMock()  # Success on second attempt
        ]
        
        client = provider.get_client()
        
        assert client is not None
        assert mock_chroma.PersistentClient.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep between retries

def test_chroma_client_provider_get_client_all_failures():
    """Test client retrieval when all connection attempts fail."""
    from src.services.vector_store import ChromaClientProvider, HAS_CHROMA
    
    if not HAS_CHROMA:
        pytest.skip("ChromaDB not available")
        
    provider = ChromaClientProvider()
    
    # Mock the chromadb module to always fail
    with patch('src.services.vector_store.chromadb') as mock_chroma:
        mock_chroma.PersistentClient.side_effect = Exception("Connection failed")
        
        client = provider.get_client()
        
        assert client is None
        # Should try 3 times (default retries)
        assert mock_chroma.PersistentClient.call_count == 3

def test_chroma_client_provider_get_client_no_chroma():
    """Test client retrieval when ChromaDB is not available."""
    from src.services.vector_store import ChromaClientProvider
    
    # Temporarily set HAS_CHROMA to False
    with patch('src.services.vector_store.HAS_CHROMA', False):
        provider = ChromaClientProvider()
        client = provider.get_client()
        assert client is None

def test_chroma_client_provider_close():
    """Test closing the ChromaDB client connection."""
    from src.services.vector_store import ChromaClientProvider
    
    provider = ChromaClientProvider()
    mock_client = MagicMock()
    provider._client = mock_client
    
    provider.close()
    
    assert provider._client is None
    # Note: PersistentClient doesn't have a close method, so none is called

# Test ChromaVectorStore initialization and collection management
def test_chroma_vector_store_init():
    """Test ChromaVectorStore initialization."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    store = ChromaVectorStore(client_provider=mock_provider)
    
    assert store.client_provider == mock_provider
    assert store._collections == {}
    assert store._initialized_collections == set()
    assert store._bm25_indexes == {}

def test_chroma_vector_store_client_property():
    """Test ChromaVectorStore client property."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    client = store.client
    
    assert client == mock_client
    mock_provider.get_client.assert_called_once()

def test_chroma_vector_store_initialize_collections():
    """Test ChromaVectorStore initialize_collections method."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, CollectionType, CollectionConfig
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    # Mock _ensure_collection to return True
    with patch.object(store, '_ensure_collection', return_value=True) as mock_ensure:
        # Test with None (should use default collections)
        result = store.initialize_collections()
        
        # Should initialize all default collections
        assert len(result) == len(CollectionType)
        for collection_type in CollectionType:
            # Actually, we need to check DEFAULT_COLLECTIONS
            from src.services.vector_store import DEFAULT_COLLECTIONS
            assert result[DEFAULT_COLLECTIONS[collection_type].name] == True
            
        # Verify _ensure_collection was called for each collection type
        assert mock_ensure.call_count == len(CollectionType)
        
        # Test with specific collection types
        specific_types = [CollectionType.STYLE_MEMORY, CollectionType.CHARACTER_MEMORY]
        result = store.initialize_collections(collection_types=specific_types)
        
        assert len(result) == 2
        assert result["style_memory"] == True
        assert result["character_memory"] == True

def test_chroma_vector_store_ensure_collection_success():
    """Test ChromaVectorStore _ensure_collection method success case."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, CollectionConfig
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    # Mock get_collection to raise Exception (collection doesn't exist)
    # Mock create_collection to succeed
    mock_collection = MagicMock()
    mock_client.get_collection.side_effect = Exception("Not found")
    mock_client.get_or_create_collection.return_value = mock_collection
    
    config = CollectionConfig(name="test_collection")
    
    result = store._ensure_collection(config)
    
    assert result == True
    assert "test_collection" in store._collections
    assert "test_collection" in store._initialized_collections
    mock_client.get_or_create_collection.assert_called_once_with(
        name="test_collection", 
        metadata=config.get_metadata()
    )

def test_chroma_vector_store_ensure_collection_exists():
    """Test ChromaVectorStore _ensure_collection method when collection exists."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, CollectionConfig
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    # Mock get_collection to return existing collection
    mock_collection = MagicMock()
    mock_collection.metadata = {"hnsw:space": "cosine"}
    mock_client.get_collection.return_value = mock_collection
    
    # Also mock get_or_create_collection to return the same collection (existing one)
    mock_client.get_or_create_collection.return_value = mock_collection
    
    config = CollectionConfig(name="test_collection", space="cosine")
    
    result = store._ensure_collection(config)
    
    assert result == True
    assert "test_collection" in store._collections
    assert "test_collection" in store._initialized_collections
    mock_client.get_collection.assert_called_once_with(name="test_collection")
    # Should still call get_or_create_collection (it gets or creates)
    mock_client.get_or_create_collection.assert_called_once_with(
        name="test_collection", 
        metadata={'hnsw:space': 'cosine', 'description': '', 
                 'hnsw:construction_ef': 100, 'hnsw:search_ef': 50, 'hnsw:M': 16}
    )

def test_chroma_vector_store_ensure_collection_different_space_warning():
    """Test ChromaVectorStore _ensure_collection method warns on different space."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, CollectionConfig
    import logging
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    # Mock get_collection to return existing collection with different space
    mock_collection = MagicMock()
    mock_collection.metadata = {"hnsw:space": "l2"}  # Different from config
    mock_client.get_collection.return_value = mock_collection
    
    config = CollectionConfig(name="test_collection", space="cosine")
    
    with patch('src.services.vector_store.logger') as mock_logger:
        result = store._ensure_collection(config)
        
        assert result == True
        # Should log a warning about different space
        mock_logger.warning.assert_called()

def test_chroma_vector_store_ensure_collection_failure():
    """Test ChromaVectorStore _ensure_collection method failure case."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, CollectionConfig
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    # Mock get_collection to raise Exception
    # Mock get_or_create_collection to also raise Exception
    mock_client.get_collection.side_effect = Exception("Database error")
    mock_client.get_or_create_collection.side_effect = Exception("Creation failed")
    
    config = CollectionConfig(name="test_collection")
    
    result = store._ensure_collection(config)
    
    assert result == False
    assert "test_collection" not in store._collections
    assert "test_collection" not in store._initialized_collections

def test_chroma_vector_store_get_collection():
    """Test ChromaVectorStore get_collection method."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    # Test when collection doesn't exist
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    
    collection = store.get_collection("test_collection")
    
    assert collection == mock_collection
    assert "test_collection" in store._collections
    mock_client.get_or_create_collection.assert_called_once_with(
        name="test_collection", 
        metadata=None
    )
    
    # Test when collection already exists
    mock_client.reset_mock()
    collection2 = store.get_collection("test_collection")
    
    assert collection2 == mock_collection
    # Should not call get_or_create_collection again
    mock_client.get_or_create_collection.assert_not_called()

def test_chroma_vector_store_get_collection_no_client():
    """Test ChromaVectorStore get_collection method when no client available."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_provider.get_client.return_value = None  # No client available
    
    store = ChromaVectorStore(client_provider=mock_provider)
    
    collection = store.get_collection("test_collection")
    
    assert collection is None

def test_chroma_vector_store_get_collection_config():
    """Test ChromaVectorStore get_collection_config method."""
    from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, CollectionType
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    store = ChromaVectorStore(client_provider=mock_provider)
    
    config = store.get_collection_config(CollectionType.STYLE_MEMORY)
    
    from src.services.vector_store import DEFAULT_COLLECTIONS
    assert config == DEFAULT_COLLECTIONS[CollectionType.STYLE_MEMORY]