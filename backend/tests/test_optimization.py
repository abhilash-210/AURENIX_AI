"""
Automated Performance, Caching & Optimization Tests.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.middleware.rate_limit import RateLimiter, RateLimitMiddleware
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.cache import EmbeddingCache
from app.services.embeddings.service import EmbeddingService
from app.services.rag.context import ContextBuilder
from app.services.rag.processor import QueryProcessor
from app.services.rag.schemas import RAGQuery
from app.services.rag.service import RAGService


# ──────────────────────────────────────────────────────────────────────────────
# 1. Embedding Cache Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_embedding_cache_basic_put_get():
    cache = EmbeddingCache(max_size=10)
    vector = [0.1, 0.2, 0.3, 0.4]

    assert cache.get("hello world", "openai", "text-embedding-3-small") is None

    cache.put("hello world", "openai", "text-embedding-3-small", vector)
    cached = cache.get("hello world", "openai", "text-embedding-3-small")

    assert cached == vector
    assert cache.stats["hits"] == 1
    assert cache.stats["misses"] == 1


def test_embedding_cache_lru_eviction():
    cache = EmbeddingCache(max_size=2)

    cache.put("item1", "p", "m", [1.0])
    cache.put("item2", "p", "m", [2.0])
    # Access item1 to make it most recently used
    assert cache.get("item1", "p", "m") == [1.0]

    # Insert item3 -> item2 should be evicted (LRU)
    cache.put("item3", "p", "m", [3.0])

    assert cache.get("item1", "p", "m") == [1.0]
    assert cache.get("item2", "p", "m") is None
    assert cache.get("item3", "p", "m") == [3.0]


@pytest.mark.asyncio
async def test_embedding_service_cache_integration():
    mock_provider = MagicMock(spec=BaseEmbeddingProvider)
    mock_provider.name = "mock"
    mock_provider._default_model = "test-model"
    mock_provider.embed_batch = AsyncMock(return_value=[[0.5, 0.5], [0.8, 0.8]])

    cache = EmbeddingCache(max_size=100)
    service = EmbeddingService(providers={"mock": mock_provider}, cache=cache)

    # First call: cache miss, provider invoked
    res1 = await service.embed_batch(["alpha", "beta"], provider_name="mock")
    assert res1 == [[0.5, 0.5], [0.8, 0.8]]
    assert mock_provider.embed_batch.call_count == 1

    # Second call with same texts: cache hit, provider NOT invoked
    res2 = await service.embed_batch(["alpha", "beta"], provider_name="mock")
    assert res2 == [[0.5, 0.5], [0.8, 0.8]]
    assert mock_provider.embed_batch.call_count == 1  # Still 1, 0 network calls!


# ──────────────────────────────────────────────────────────────────────────────
# 2. Context Builder Deduplication & Budgeting Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_context_builder_deduplication():
    builder = ContextBuilder(max_context_chars=5000)
    chunks = [
        {"payload": {"chunk_text": "This is a security policy text for SOC 2."}},
        {"payload": {"chunk_text": "This is a security policy text for SOC 2."}},  # duplicate
        {"payload": {"chunk_text": "This is another different section on KMS."}},
    ]

    context = builder.build_context(chunks)
    assert context.count("Document [1]") == 1
    assert context.count("Document [2]") == 1
    assert context.count("Document [3]") == 0  # Deduplicated from 3 to 2 docs


def test_context_builder_character_budgeting():
    builder = ContextBuilder(max_context_chars=120)
    chunks = [
        {"payload": {"chunk_text": "A" * 60, "source_filename": "f1.txt"}},
        {"payload": {"chunk_text": "B" * 60, "source_filename": "f2.txt"}},
        {"payload": {"chunk_text": "C" * 60, "source_filename": "f3.txt"}},  # Should exceed budget
    ]

    context = builder.build_context(chunks)
    assert "Document [1]" in context
    assert "Document [3]" not in context  # Budget stopped inclusion


# ──────────────────────────────────────────────────────────────────────────────
# 3. Conversational Fast-Path Routing Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_query_processor_greeting_detection():
    processor = QueryProcessor()

    assert processor.is_conversational_greeting("hello") is True
    assert processor.is_conversational_greeting("Hi there!") is True
    assert processor.is_conversational_greeting("Good morning") is True
    assert processor.is_conversational_greeting("Thank you very much") is True
    assert processor.is_conversational_greeting("What is the password rotation policy in SOC 2?") is False


@pytest.mark.asyncio
async def test_rag_service_greeting_fast_path():
    rag = RAGService()
    rag.retriever.retrieve = AsyncMock()  # Mock retriever to verify it is NOT called
    rag.llm_service.complete = AsyncMock()

    mock_resp = MagicMock()
    mock_resp.content = "Hello! How can I assist you with Aurenix AI today?"
    rag.llm_service.complete.return_value = mock_resp

    response = await rag.answer_question(
        workspace_id="test-ws",
        query=RAGQuery(query="Hello there!"),
    )

    assert "Hello" in response.answer
    assert rag.retriever.retrieve.call_count == 0  # Bypassed vector DB retrieval!


# ──────────────────────────────────────────────────────────────────────────────
# 4. Rate Limiting Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_rate_limiter_allows_and_blocks():
    limiter = RateLimiter(requests_per_minute=3, window_seconds=2)
    client_key = "127.0.0.1"

    # 3 allowed requests
    for _ in range(3):
        allowed, remaining, retry_after = limiter.is_allowed(client_key)
        assert allowed is True
        assert retry_after == 0.0

    # 4th request within window -> blocked
    allowed, remaining, retry_after = limiter.is_allowed(client_key)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0.0


@pytest.mark.asyncio
async def test_rate_limit_middleware_integration():
    from starlette.applications import Starlette
    from starlette.routing import Route

    async def sample_endpoint(request):
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[Route("/test-rate-limit", sample_endpoint)],
    )
    app.add_middleware(RateLimitMiddleware, requests_per_minute=2)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        # Request 1: OK
        r1 = await ac.get("/test-rate-limit")
        assert r1.status_code == 200

        # Request 2: OK
        r2 = await ac.get("/test-rate-limit")
        assert r2.status_code == 200

        # Request 3: Rate Limited (429)
        r3 = await ac.get("/test-rate-limit")
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
        assert r3.json()["error"]["code"] == "RATE_LIMITED"
