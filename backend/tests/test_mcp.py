import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.mcp.client import HTTP_MCPClient, MCPClientTimeout
from app.services.mcp.registry import ToolRegistry
from app.services.mcp.schemas import MCPServerConfig, ToolDefinition


@pytest.fixture
def mcp_config():
    return MCPServerConfig(
        name="test_server",
        url="http://mock-mcp-server:8000",
        allowlist=["safe_tool"],
        timeout_seconds=2.0
    )


@pytest.mark.asyncio
async def test_mcp_client_list_tools_with_allowlist(mcp_config, monkeypatch):
    client = HTTP_MCPClient(mcp_config)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tools": [
            {"name": "safe_tool", "description": "Safe"},
            {"name": "dangerous_tool", "description": "Dangerous"}
        ]
    }
    
    mock_get = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(client.client, "get", mock_get)
    
    tools = await client.list_tools()
    
    # Should only return the allowlisted tool
    assert len(tools) == 1
    assert tools[0].name == "safe_tool"


@pytest.mark.asyncio
async def test_mcp_client_timeout_handling(mcp_config, monkeypatch):
    client = HTTP_MCPClient(mcp_config)
    
    # Simulate an HTTPX timeout
    mock_post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    monkeypatch.setattr(client.client, "post", mock_post)
    
    result = await client.call_tool("safe_tool", {})
    
    assert result.is_error is True
    assert "timed out" in result.content


@pytest.mark.asyncio
async def test_tool_registry_execution_rejection(monkeypatch):
    # Reset singleton for testing
    ToolRegistry._instance = None
    
    # Mock settings to inject config
    mock_settings = MagicMock()
    mock_settings.mcp_servers_config = '[{"name": "mock", "url": "http://mock", "allowlist": ["allowed"]}]'
    monkeypatch.setattr("app.services.mcp.registry.get_settings", lambda: mock_settings)
    
    registry = ToolRegistry.get_instance()
    
    # Manually register the allowed tool
    registry.tools["mock.allowed"] = ToolDefinition(
        name="mock.allowed",
        description="allowed",
        input_schema={},
        server_name="mock"
    )
    
    # Attempt to execute an unregistered/unallowed tool
    res = await registry.execute_tool("mock.dangerous", {})
    
    assert res.is_error is True
    assert "not registered or not permitted" in res.content
