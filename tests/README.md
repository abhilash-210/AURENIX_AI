# tests/

Cross-module integration and end-to-end test suites.

> **Note:** Unit tests live alongside the code they test (e.g., `backend/tests/`, `rag/tests/`).
> This directory contains **integration** and **end-to-end** tests that span multiple modules.

## Structure

```
tests/
├── integration/
│   ├── test_chat_flow.py          # Auth → chat → streaming response
│   ├── test_rag_pipeline.py       # Ingest document → query → retrieve chunks
│   └── test_agent_tool_use.py     # Agent calls tool → receives result
├── e2e/
│   └── test_full_conversation.py  # Full user journey end-to-end
├── fixtures/
│   ├── sample_documents/          # Test PDFs, TXTs for ingestion tests
│   └── conftest.py                # Shared pytest fixtures
└── README.md
```

## Running Tests

```bash
# All tests (unit + integration)
pytest

# Unit tests only (fast)
pytest backend/tests/ rag/tests/ agents/tests/

# Integration tests (requires Docker services)
pytest tests/integration/

# With coverage report
pytest --cov --cov-report=html
```

## Test Standards

- Every new module must have > 70% unit test coverage before merging
- Integration tests require Docker Compose services to be running
- LLM calls in tests are **always mocked** — no real API calls in CI
- Test data lives in `tests/fixtures/` — never use production data
