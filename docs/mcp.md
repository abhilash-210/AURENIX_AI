# Aurenix AI — Model Context Protocol (MCP) Integration

> **Module:** `backend/app/services/mcp/`  
> **Standard:** Anthropic Model Context Protocol (JSON-RPC 2.0)  
> **Status:** Production-Ready | Multi-Transport (Stdio & SSE)

---

## 1. Overview & Standard Alignment

Aurenix AI implements the **Model Context Protocol (MCP)** specification, allowing LLMs to discover, inspect, and invoke tools, resources, and prompt templates exposed by standard MCP servers across Stdio or SSE transports.

```
                      ┌─────────────────────────────────┐
                      │    Aurenix AI Agent Engine      │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │        MCP Client Gateway       │
                      │    • Tool Allowlisting          │
                      │    • JSON-RPC 2.0 Transport     │
                      │    • Timeout & Error Wrapping   │
                      └────────────────┬────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
        ┌─────────────────────────┐         ┌─────────────────────────┐
        │  Stdio MCP Server Subprocess  │   │  Remote SSE MCP Server  │
        │  (e.g., SQLite / Git)   │         │  (e.g., Enterprise API) │
        └─────────────────────────┘         └─────────────────────────┘
```

---

## 2. MCP Client Capabilities

1. **Dynamic Tool Discovery (`tools/list`)**: Queries configured MCP servers to retrieve available tool names, descriptions, and JSON Schemas.
2. **Strict Tool Allowlisting**: System administrators can configure `allowed_tools` lists to prevent unauthorized tool execution.
3. **Async JSON-RPC Protocol**: Communicates via standard JSON-RPC 2.0 envelopes with deterministic request ID correlation and timeout guards.
