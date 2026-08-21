import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory, MemoryScope
from app.services.memory.service import MemoryService


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_vector_store(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("app.services.memory.service.VectorStoreService.get_instance", lambda: mock)
    return mock


@pytest.mark.asyncio
async def test_get_memories_scoping(mock_db, mock_vector_store, monkeypatch):
    service = MemoryService(mock_db)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        Memory(id=uuid.uuid4(), scope=MemoryScope.USER, content="User preference"),
    ]
    mock_db.execute.return_value = mock_result
    
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    memories = await service.get_memories(workspace_id, user_id)
    
    assert len(memories) == 1
    assert memories[0].content == "User preference"
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_memory_cascades_to_qdrant(mock_db, mock_vector_store, monkeypatch):
    service = MemoryService(mock_db)
    
    mem_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Memory(id=mem_id, user_id=user_id)
    mock_db.execute.return_value = mock_result
    
    await service.delete_memory(mem_id, user_id)
    
    # Assert DB delete
    mock_db.delete.assert_called_once()
    mock_db.commit.assert_called_once()
    
    # Assert Qdrant delete
    mock_vector_store.delete_memory_vector.assert_called_once_with(str(mem_id))


@pytest.mark.asyncio
async def test_extract_and_save_memories_ignores_empty(mock_db, mock_vector_store, monkeypatch):
    service = MemoryService(mock_db)
    
    # Mock LLM returning empty facts
    mock_llm = AsyncMock()
    from app.services.memory.schemas import MemoryExtractionResult
    mock_response = AsyncMock()
    mock_response.parsed = MemoryExtractionResult(memories=[])
    mock_llm.complete_structured.return_value = mock_response
    service.llm = mock_llm
    
    exchange = [{"role": "user", "content": "hello"}]
    
    await service.extract_and_save_memories(exchange, uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    
    # Should not save anything to DB
    mock_db.add.assert_not_called()
    mock_vector_store.upsert_memory_vectors.assert_not_called()
