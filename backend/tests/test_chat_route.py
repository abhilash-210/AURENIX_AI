"""
Integration tests for POST /api/v1/chat endpoint.
"""

from __future__ import annotations

import json
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.routes.chat import get_llm_service
from app.services.llm import LLMService, MockLLMProvider


@pytest.fixture
def mock_llm_service() -> LLMService:
    provider = MockLLMProvider(default_response="Test endpoint response")
    return LLMService(providers={"mock": provider, "openai": provider, "anthropic": provider})


@pytest.fixture
def app_with_mock_llm(mock_llm_service: LLMService):
    app = create_app()
    app.dependency_overrides[get_llm_service] = lambda: mock_llm_service
    return app


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_completion_json_success(self, app_with_mock_llm):
        transport = ASGITransport(app=app_with_mock_llm)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "provider": "mock",
                "stream": False,
            }
            response = await client.post("/api/v1/chat", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "meta" in data
            assert data["data"]["content"].startswith("Test endpoint response")
            assert data["data"]["provider"] == "mock"
            assert data["meta"]["request_id"] is not None

    @pytest.mark.asyncio
    async def test_chat_completion_validation_error(self, app_with_mock_llm):
        transport = ASGITransport(app=app_with_mock_llm)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Empty messages list should trigger Pydantic validation error (422)
            payload = {"messages": [], "provider": "mock"}
            response = await client.post("/api/v1/chat", json=payload)

            assert response.status_code == 422
            data = response.json()
            assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_chat_completion_streaming_sse(self, app_with_mock_llm):
        transport = ASGITransport(app=app_with_mock_llm)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "messages": [{"role": "user", "content": "Tell me a story"}],
                "provider": "mock",
                "stream": True,
            }
            response = await client.post("/api/v1/chat", json=payload)

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            content = response.text
            assert "data: " in content
            assert "data: [DONE]" in content

            # Parse streamed chunks
            lines = [line.strip() for line in content.split("\n") if line.startswith("data: ")]
            assert len(lines) >= 2
            first_chunk_json = json.loads(lines[0][6:])
            assert "delta" in first_chunk_json
