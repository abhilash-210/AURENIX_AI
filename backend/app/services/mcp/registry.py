"""
Tool Registry for managing MCP clients and normalizing tools.
"""

import json
import logging
from typing import Any

from app.config import get_settings
from app.services.mcp.client import HTTP_MCPClient
from app.services.mcp.schemas import MCPServerConfig, ToolCallResult, ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for managing trusted MCP servers and routing tool calls.
    Implemented as a Singleton for caching discovered tools.
    """
    _instance = None
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.clients: dict[str, HTTP_MCPClient] = {}
        self.tools: dict[str, ToolDefinition] = {}
        
        # Load configs
        try:
            configs_data = json.loads(self.settings.mcp_servers_config)
            for config_dict in configs_data:
                config = MCPServerConfig(**config_dict)
                self.clients[config.name] = HTTP_MCPClient(config)
        except Exception as exc:
            logger.error(f"Failed to parse MCP server configs: {exc}")

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self) -> None:
        """
        Discovers and caches tools from all configured clients.
        """
        for server_name, client in self.clients.items():
            try:
                server_tools = await client.list_tools()
                for tool in server_tools:
                    # Namespace tools to avoid collisions: "server_name.tool_name"
                    namespaced_name = f"{server_name}.{tool.name}"
                    tool.name = namespaced_name
                    self.tools[namespaced_name] = tool
            except Exception as exc:
                logger.warning(f"Failed to initialize tools for {server_name}: {exc}")

    def get_all_tools(self) -> list[ToolDefinition]:
        return list(self.tools.values())

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallResult:
        """
        Route a tool call to the appropriate MCP client.
        """
        tool_def = self.tools.get(tool_name)
        if not tool_def:
            return ToolCallResult(
                tool_name=tool_name,
                content=f"Tool {tool_name} is not registered or not permitted.",
                is_error=True
            )
            
        client = self.clients.get(tool_def.server_name)
        if not client:
            return ToolCallResult(
                tool_name=tool_name,
                content=f"Server {tool_def.server_name} is unavailable.",
                is_error=True
            )
            
        # Strip the namespace before sending to the server
        original_tool_name = tool_name.split(".", 1)[-1]
        
        logger.info(f"Executing MCP Tool: {tool_name}")
        return await client.call_tool(original_tool_name, arguments)
