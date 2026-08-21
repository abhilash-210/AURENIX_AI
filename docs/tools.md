# Aurenix AI — Tool Calling Subsystem & Registry

> **Module:** `backend/app/services/mcp/registry.py` & `backend/app/services/agents/`  
> **Status:** Production-Ready | Schema Validated | Sandboxed

---

## 1. Tool System Architecture

The Tool Calling subsystem allows LLM agents to perform validated real-world actions with strict JSON Schema contracts, input sanitization, and execution timeouts.

```
                      ┌────────────────────────────┐
                      │    Agent Execution Loop    │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │    Tool Registry Lookup    │
                      │    • Name Resolution       │
                      │    • Permission Check      │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │    Schema Validation       │
                      │    (Pydantic / JSONSchema) │
                      └─────────────┬──────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
        ┌─────────────────────────┐   ┌─────────────────────────┐
        │ 1. Built-in Local Tools │   │ 2. Remote MCP Tools     │
        │ • Vector Search         │   │ • Filesystem / Shell    │
        │ • Calculator / Math     │   │ • External API Gateways │
        │ • Web / Document Parser │   │ • Database Querying     │
        └────────────┬────────────┘   └────────────┬────────────┘
                     │                             │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │    Execution Sandbox       │
                      │    • Timeout Enforcement   │
                      │    • Audit Log Recording   │
                      └────────────────────────────┘
```

---

## 2. Tool Definition & Registry Pattern

```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    is_safe: bool = True
    timeout_seconds: float = 10.0
```

Each tool implements an async `execute(params: dict[str, Any]) -> dict[str, Any]` method. Exceptions during execution are caught and wrapped in structured `ToolExecutionError` payloads rather than crashing the agent graph.
