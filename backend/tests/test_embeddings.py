import pytest

from app.exceptions import LLMProviderError
from app.services.embeddings.providers.mock import MockEmbeddingProvider
from app.services.embeddings.service import EmbeddingService


@pytest.mark.asyncio
async def test_mock_embedding_provider():
    provider = MockEmbeddingProvider(vector_size=10)
    
    vec1 = await provider.embed_text("Hello World")
    vec2 = await provider.embed_text("Hello World")
    vec3 = await provider.embed_text("Different")
    
    assert len(vec1) == 10
    assert vec1 == vec2  # Deterministic hashing
    assert vec1 != vec3  # Different inputs yield different vectors


@pytest.mark.asyncio
async def test_embedding_service_mock_fallback(monkeypatch):
    # Missing API key should fallback to mock
    monkeypatch.setenv("OPENAI_API_KEY", "")
    
    service = EmbeddingService()
    provider = service.get_provider("openai")
    
    assert provider.name == "mock"


@pytest.mark.asyncio
async def test_embedding_service_embed_batch():
    service = EmbeddingService()
    # Force use of mock provider for tests
    results = await service.embed_batch(["test1", "test2"], provider_name="mock")
    
    assert len(results) == 2
    assert len(results[0]) == 1536  # Default mock size
    assert len(results[1]) == 1536
