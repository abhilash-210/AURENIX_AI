"""
MCP Client for HTTP-based interactions.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.exceptions import AurenixError
from app.services.mcp.schemas import MCPServerConfig, ToolCallResult, ToolDefinition

logger = logging.getLogger(__name__)


class MCPClientError(AurenixError):
    pass


class MCPClientTimeout(MCPClientError):
    pass


class HTTP_MCPClient:
    """
    Lightweight REST-based MCP Client.
    Connects to a trusted MCP server to discover and execute tools.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.client = httpx.AsyncClient(timeout=self.config.timeout_seconds)

    async def list_tools(self) -> list[ToolDefinition]:
        """
        Fetch available tools from the MCP server.
        """
        try:
            # Assuming standard JSON-RPC or REST discovery endpoint
            # For this MVP, we simulate a standard REST /tools endpoint
            response = await self.client.get(f"{self.config.url.rstrip('/')}/tools")
            response.raise_for_status()
            data = response.json()
            
            tools = []
            for item in data.get("tools", []):
                # Filter against allowlist if configured
                if self.config.allowlist is not None and item["name"] not in self.config.allowlist:
                    continue
                    
                tools.append(ToolDefinition(
                    name=item["name"],
                    description=item["description"],
                    input_schema=item.get("input_schema", {}),
                    server_name=self.config.name,
                ))
            return tools
        except httpx.TimeoutException as exc:
            logger.error(f"MCP Server {self.config.name} timeout during discovery.")
            raise MCPClientTimeout(f"Timeout discovering tools from {self.config.name}") from exc
        except Exception as exc:
            logger.error(f"MCP Server {self.config.name} connection failed: {exc}")
            raise MCPClientError(f"Failed to discover tools from {self.config.name}") from exc

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        """
        Execute a tool on the MCP server with strict timeouts.
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call_tool",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
                "id": 1,
            }
            
            # Use asyncio.wait_for as a secondary hard timeout safeguard
            response = await asyncio.wait_for(
                self.client.post(f"{self.config.url.rstrip('/')}/call", json=payload),
                timeout=self.config.timeout_seconds + 2.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                return ToolCallResult(
                    tool_name=tool_name,
                    content=str(data["error"]),
                    is_error=True
                )
                
            return ToolCallResult(
                tool_name=tool_name,
                content=data.get("result", {}).get("content", "Success"),
                is_error=False
            )
            
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            logger.error(f"MCP Tool {tool_name} timed out.")
            return ToolCallResult(
                tool_name=tool_name,
                content="Tool execution timed out.",
                is_error=True
            )
        except Exception as exc:
            logger.error(f"MCP Tool {tool_name} failed: {exc}")
            return ToolCallResult(
                tool_name=tool_name,
                content=f"Tool execution failed: {str(exc)}",
                is_error=True
            )
