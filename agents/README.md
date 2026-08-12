# agents/

Multi-agent orchestration layer — supervisor routing and specialist agent definitions.

**Planned Sprint:** Sprint 3

## Responsibilities

- Supervisor agent: intent classification and routing to specialist agents
- Specialist agents: Research, Q&A, Summarisation, Code
- LangGraph state machine definitions
- Versioned system prompt templates
- Agent-level streaming integration

## Structure (Sprint 3)

```
agents/
├── supervisor/
│   ├── graph.py          # LangGraph supervisor graph definition
│   ├── router.py         # Intent classification logic
│   └── prompts/
│       └── supervisor_v1.txt
├── specialists/
│   ├── research.py       # Research agent (RAG + web search)
│   ├── qa.py             # Q&A agent with citations
│   ├── summarisation.py  # Document summarisation agent
│   └── prompts/
├── base.py               # BaseAgent abstract class
├── registry.py           # Agent registry
└── tests/
```

## Topology

```
User Query → Supervisor → Specialist Agent → Tools → Response
```

> See [`docs/architecture.md`](../docs/architecture.md) and [`docs/ai-concepts.md`](../docs/ai-concepts.md) for full specification.
