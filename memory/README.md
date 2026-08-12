# memory/

Multi-horizon memory system — short-term, long-term, and episodic context storage.

**Planned Sprint:** Sprint 4

## Responsibilities

- **Short-term memory:** Redis-backed conversation window for current session
- **Long-term memory:** PostgreSQL-persisted user facts and preferences
- **Episodic memory:** Timestamped interaction log with relevance scoring
- Memory injection into agent context before each LLM call

## Structure (Sprint 4)

```
memory/
├── short_term/
│   ├── store.py          # Redis read/write with TTL
│   └── window.py         # Sliding window management
├── long_term/
│   ├── store.py          # PostgreSQL fact persistence
│   └── extractor.py      # LLM-based fact extraction from turns
├── episodic/
│   ├── store.py          # Timestamped interaction logging
│   └── retriever.py      # Relevance-scored episode retrieval
├── manager.py            # Unified MemoryManager facade
└── tests/
```

## Memory Horizons

| Layer | Storage | Scope | Retention |
|---|---|---|---|
| Short-term | Redis | Current conversation | Session lifetime |
| Long-term | PostgreSQL | User-level facts | Indefinite |
| Episodic | PostgreSQL | Interaction log | Configurable |

> See [`docs/architecture.md`](../docs/architecture.md) and [`docs/ai-concepts.md`](../docs/ai-concepts.md) for memory system design.
