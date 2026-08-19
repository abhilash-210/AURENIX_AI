"""
MCP Integration Schemas.
"""

from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """
    Standardized tool schema exposed to the LLM.
    """
    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str = Field(description="The internal MCP server routing name.")


class MCPServerConfig(BaseModel):
    """
    Configuration for a trusted MCP server.
    """
    name: str
    url: str
    allowlist: list[str] | None = Field(default=None, description="List of allowed tool names. If None, all discovered tools are allowed.")
    timeout_seconds: float = Field(default=10.0)


class ToolCallRequest(BaseModel):
    """
    Request payload when an agent wants to call a tool.
    """
    tool_name: str
    arguments: dict[str, Any]


class ToolCallResult(BaseModel):
    """
    Result returned from an MCP tool call.
    """
    tool_name: str
    content: str | dict[str, Any]
    is_error: bool = False
