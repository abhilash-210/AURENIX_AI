# evaluation/

Automated quality framework — RAGAS-based scoring for every LLM response.

**Planned Sprint:** Sprint 6

## Responsibilities

- Asynchronous evaluation of every agent response (non-blocking)
- RAGAS metrics: faithfulness, answer relevance, context precision, context recall
- Hallucination rate tracking
- Metric persistence to PostgreSQL
- Aggregate reporting API

## Structure (Sprint 6)

```
evaluation/
├── metrics/
│   ├── faithfulness.py   # Claim extraction + context verification
│   ├── relevance.py      # Answer relevance scoring
│   ├── precision.py      # Context precision metric
│   └── recall.py         # Context recall (requires reference answer)
├── pipeline.py           # Async evaluation orchestrator
├── store.py              # Metric persistence to PostgreSQL
├── reporter.py           # Aggregate report generation
└── tests/
```

## Metrics Reference

| Metric | Range | Good Score |
|---|---|---|
| Faithfulness | 0–1 | > 0.85 |
| Answer Relevance | 0–1 | > 0.80 |
| Context Precision | 0–1 | > 0.75 |
| Hallucination Rate | 0–1 | < 0.05 |

> See [`docs/ai-concepts.md`](../docs/ai-concepts.md#6-evaluation) for metric explanations.
