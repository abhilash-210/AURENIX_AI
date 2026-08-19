import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.agents.graph import should_continue
from app.services.agents.service import AgentOrchestratorService


@pytest.fixture
def mock_llm_service(monkeypatch):
    mock = AsyncMock()
    # By default, mock the complete and complete_structured methods
    # to return successful outputs.
    monkeypatch.setattr("app.services.agents.nodes.LLMService", mock)
    return mock


@pytest.mark.asyncio
async def test_agent_orchestrator_success(monkeypatch):
    # Mock LLM Service specifically for each node type
    # For simplicity, we just mock the nodes to ensure graph flows properly
    mock_planner = AsyncMock(return_value={"plan": "Test plan", "search_queries": ["q1"], "iterations": 1})
    mock_retriever = AsyncMock(return_value={"retrieved_documents": [{"id": "1", "payload": {"chunk_text": "data"}}]})
    mock_research = AsyncMock(return_value={"analysis": "Here is the answer."})
    mock_critic = AsyncMock(return_value={"is_approved": True, "critic_feedback": "Looks good."})
    mock_final = AsyncMock(return_value={"final_answer": "Here is the answer."})

    monkeypatch.setattr("app.services.agents.graph.planner_node", mock_planner)
    monkeypatch.setattr("app.services.agents.graph.retriever_node", mock_retriever)
    monkeypatch.setattr("app.services.agents.graph.research_node", mock_research)
    monkeypatch.setattr("app.services.agents.graph.critic_node", mock_critic)
    monkeypatch.setattr("app.services.agents.graph.final_answer_node", mock_final)

    service = AgentOrchestratorService()
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    result = await service.execute_query(workspace_id, user_id, "test query")
    
    assert result["answer"] == "Here is the answer."
    # Since we mocked the nodes, the actual nodes aren't pushing to the graph's internal states,
    # but the LangGraph compiled state machine will call them in order.


def test_should_continue():
    # If approved, route to final_answer
    state1 = {"is_approved": True, "iterations": 1}
    assert should_continue(state1) == "final_answer_node"
    
    # If rejected but max iterations hit, route to final_answer
    state2 = {"is_approved": False, "iterations": 3}
    assert should_continue(state2) == "final_answer_node"
    
    # If rejected and under limit, route to retriever
    state3 = {"is_approved": False, "iterations": 1}
    assert should_continue(state3) == "retriever_node"
