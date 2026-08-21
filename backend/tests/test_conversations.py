import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ForbiddenError, NotFoundError
from app.models.chat import Conversation, Message
from app.schemas.conversation import ConversationCreate
from app.services.chat.service import ChatService


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.mark.asyncio
async def test_create_conversation(mock_db):
    service = ChatService(mock_db)
    workspace_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    
    data = ConversationCreate(title="Test Chat")
    
    # Simple assert since DB adds it
    conv = await service.create_conversation(workspace_id, owner_id, data)
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert conv.title == "Test Chat"
    assert conv.workspace_id == workspace_id


@pytest.mark.asyncio
async def test_get_conversation_forbidden(mock_db, monkeypatch):
    # Setup mock to return a conversation with a different owner
    mock_result = MagicMock()
    mock_conv = Conversation(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
    )
    mock_result.scalar_one_or_none.return_value = mock_conv
    mock_db.execute.return_value = mock_result
    
    service = ChatService(mock_db)
    
    with pytest.raises(ForbiddenError):
        await service.get_conversation(mock_conv.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_get_conversation_not_found(mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    service = ChatService(mock_db)
    
    with pytest.raises(NotFoundError):
        await service.get_conversation(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_stream_rag_chat_no_results(mock_db, monkeypatch):
    # Mock get_conversation
    mock_conv = Conversation(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
    )
    
    # Mock the DB calls for fetching history (empty for now)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    service = ChatService(mock_db)
    monkeypatch.setattr(service, "get_conversation", AsyncMock(return_value=mock_conv))
    
    # Mock Retriever returning empty list
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = []
    service.retriever = mock_retriever
    
    generator = service.stream_rag_chat(mock_conv.id, mock_conv.owner_id, "Hello")
    
    chunks = []
    async for chunk in generator:
        chunks.append(chunk)
        
    assert len(chunks) == 2
    assert "data: [DONE]" in chunks[1]
    
    # Verify two DB adds (user msg + assistant fallback msg)
    assert mock_db.add.call_count == 2
