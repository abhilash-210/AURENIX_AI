# tools/

Pluggable tool registry — capability extensions for agents via a self-registering adapter pattern.

**Planned Sprint:** Sprint 3

## Responsibilities

- Tool registry with decorator-based self-registration
- Typed input/output schemas for every tool
- Adapter implementations: web search, calculator, SQL query, file reader
- Graceful error handling with circuit-breaker pattern

## Structure (Sprint 3)

```
tools/
├── base.py               # BaseTool abstract class (name, description, input_schema, run)
├── registry.py           # ToolRegistry with @register_tool decorator
├── adapters/
│   ├── web_search.py     # Tavily API adapter
│   ├── calculator.py     # Safe math expression evaluator
│   ├── sql_query.py      # Read-only SQL executor (Sprint 4+)
│   └── file_reader.py    # Local/GCS file content reader
└── tests/
```

## Tool Interface

Every tool implements:

```python
class BaseTool:
    name: str
    description: str
    input_schema: dict       # JSON Schema for LLM function calling
    def run(self, **kwargs) -> ToolResult: ...
```

> See [`docs/architecture.md`](../docs/architecture.md) for the tool integration design.
