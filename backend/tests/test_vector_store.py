import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.vector_store.qdrant import QdrantVectorStore
from app.services.vector_store.service import VectorStoreService


@pytest.fixture
def mock_qdrant_client(monkeypatch):
    mock_client = AsyncMock()
    
    # Mock qdrant client init
    def _init(*args, **kwargs):
        return mock_client
        
    monkeypatch.setattr("app.services.vector_store.qdrant.AsyncQdrantClient", _init)
    return mock_client


@pytest.mark.asyncio
async def test_qdrant_ensure_collection(mock_qdrant_client):
    # Collection does not exist
    mock_collections = MagicMock()
    mock_collections.collections = []
    mock_qdrant_client.get_collections.return_value = mock_collections
    
    store = QdrantVectorStore()
    await store.ensure_collection_exists(1536)
    
    mock_qdrant_client.create_collection.assert_called_once()
    mock_qdrant_client.create_payload_index.assert_called_once()


@pytest.mark.asyncio
async def test_vector_store_service_indexing(monkeypatch):
    # Mock out vector store and embeddings
    mock_upsert = AsyncMock()
    monkeypatch.setattr("app.services.vector_store.qdrant.QdrantVectorStore.upsert_vectors", mock_upsert)
    
    service = VectorStoreService()
    workspace_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    
    chunks = [
        {"id": "c1", "content": "hello world", "page_number": 1},
        {"id": "c2", "content": "test chunk", "page_number": 2},
    ]
    
    # We can just use the mock provider for embeddings
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    
    await service.index_document(workspace_id, doc_id, chunks, "test.pdf")
    
    mock_upsert.assert_called_once()
    kwargs = mock_upsert.call_args.kwargs
    assert len(kwargs["vectors"]) == 2
    assert len(kwargs["payloads"]) == 2
    assert kwargs["payloads"][0]["chunk_text"] == "hello world"
    assert kwargs["payloads"][0]["workspace_id"] == workspace_id
    assert kwargs["payloads"][0]["source_filename"] == "test.pdf"


@pytest.mark.asyncio
async def test_vector_store_service_search(monkeypatch):
    mock_search = AsyncMock()
    # Mock return search results
    from app.services.vector_store.base import SearchResult
    mock_search.return_value = [
        SearchResult(id="1", score=0.95, payload={"chunk_text": "match"}),
    ]
    
    monkeypatch.setattr("app.services.vector_store.qdrant.QdrantVectorStore.search_similar", mock_search)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    
    service = VectorStoreService()
    workspace_id = str(uuid.uuid4())
    
    results = await service.search(workspace_id, "query text")
    
    assert len(results) == 1
    assert results[0]["score"] == 0.95
    assert results[0]["payload"]["chunk_text"] == "match"
    mock_search.assert_called_once()
