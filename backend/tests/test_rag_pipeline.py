import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.rag.schemas import RAGQuery
from app.services.rag.service import RAGService


@pytest.fixture
def mock_retriever(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("app.services.rag.service.Retriever.retrieve", mock)
    return mock


@pytest.fixture
def mock_llm_service(monkeypatch):
    mock = AsyncMock()
    
    # Return a dummy completion response
    from app.services.llm.types import ChatCompletionResponse, UsageInfo
    
    mock.return_value = ChatCompletionResponse(
        content="This is a grounded answer citing [1].",
        role="assistant",
        model="mock",
        provider="mock",
        usage=UsageInfo(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        finish_reason="stop",
    )
    
    monkeypatch.setattr("app.services.rag.service.LLMService.complete", mock)
    return mock


@pytest.mark.asyncio
async def test_rag_service_relevant_question(mock_retriever, mock_llm_service):
    workspace_id = str(uuid.uuid4())
    query = RAGQuery(query="What is Aurenix AI?")
    
    mock_retriever.return_value = [
        {
            "id": "1",
            "score": 0.9,
            "payload": {
                "document_id": "d1",
                "chunk_id": "c1",
                "source_filename": "about.pdf",
                "page_number": 1,
                "chunk_text": "Aurenix AI is a powerful assistant.",
            }
        }
    ]
    
    service = RAGService()
    response = await service.answer_question(workspace_id, query)
    
    assert response.answer == "This is a grounded answer citing [1]."
    assert len(response.citations) == 1
    assert response.citations[0].citation_id == "[1]"
    assert response.citations[0].source.source_filename == "about.pdf"


@pytest.mark.asyncio
async def test_rag_service_no_results(mock_retriever, mock_llm_service):
    workspace_id = str(uuid.uuid4())
    query = RAGQuery(query="What is Aurenix AI?")
    
    # Return empty list to simulate no results
    mock_retriever.return_value = []
    
    service = RAGService()
    response = await service.answer_question(workspace_id, query)
    
    assert "couldn't find any relevant documents" in response.answer
    assert len(response.citations) == 0
    # LLM should not be called if no documents are found
    mock_llm_service.assert_not_called()


@pytest.mark.asyncio
async def test_rag_service_workspace_isolation(mock_retriever, mock_llm_service):
    workspace_id = str(uuid.uuid4())
    query = RAGQuery(query="What is Aurenix AI?")
    
    mock_retriever.return_value = []
    
    service = RAGService()
    await service.answer_question(workspace_id, query)
    
    # Verify the workspace ID was passed to the retriever
    mock_retriever.assert_called_once()
    kwargs = mock_retriever.call_args.kwargs
    assert kwargs["workspace_id"] == workspace_id
