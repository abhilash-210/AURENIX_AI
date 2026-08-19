import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_analytics_overview_unauthorized(async_client: AsyncClient, setup_workspaces):
    workspace, _ = setup_workspaces
    
    # Try accessing without auth token
    response = await async_client.get(f"/api/v1/workspaces/{workspace.id}/analytics/overview")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_analytics_overview_authorized(async_client: AsyncClient, auth_token: str, setup_workspaces):
    workspace, _ = setup_workspaces
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await async_client.get(f"/api/v1/workspaces/{workspace.id}/analytics/overview", headers=headers)
    
    assert response.status_code == 200
    data = response.json()["data"]
    
    # Check that required keys are present
    assert "documents" in data
    assert "conversations" in data
    assert "ai_requests" in data
    
    # Check that unavailable metrics are explicitly null
    assert data["agent_executions"] is None
    assert data["retrieval_operations"] is None
    assert data["response_latency"] is None
    assert data["token_usage"] is None
    assert data["errors"] is None


@pytest.mark.asyncio
async def test_analytics_activity_authorized(async_client: AsyncClient, auth_token: str, setup_workspaces):
    workspace, _ = setup_workspaces
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await async_client.get(f"/api/v1/workspaces/{workspace.id}/analytics/activity", headers=headers)
    
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert "recent_documents" in data
    assert "recent_conversations" in data
    assert isinstance(data["recent_documents"], list)
    assert isinstance(data["recent_conversations"], list)
