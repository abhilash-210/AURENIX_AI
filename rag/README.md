# rag/

Retrieval-Augmented Generation pipeline — document ingestion, embedding, and hybrid retrieval.

**Planned Sprint:** Sprint 2

## Responsibilities

- Document loading: PDF, DOCX, TXT, URL
- Text chunking with configurable size and overlap
- Embedding generation (OpenAI or local model, env-switchable)
- Vector store management (ChromaDB dev / pgvector prod)
- Hybrid retrieval: semantic + BM25, fused via RRF
- Optional re-ranking via cross-encoder

## Structure (Sprint 2)

```
rag/
├── ingestion/
│   ├── loader.py         # Document format adapters
│   ├── chunker.py        # Recursive text splitter
│   └── pipeline.py       # Orchestrates load → chunk → embed → store
├── embedding/
│   ├── base.py           # EmbeddingProvider abstract class
│   └── openai.py         # OpenAI embedding adapter
├── retrieval/
│   ├── semantic.py       # Vector similarity search
│   ├── bm25.py           # Keyword retrieval
│   └── fusion.py         # Reciprocal Rank Fusion
├── store/
│   ├── base.py           # VectorStore abstract class
│   └── chroma.py         # ChromaDB adapter
└── tests/
```

## Key Design Decisions

- Provider-agnostic via abstract base classes — swap embeddings without rewriting retrieval
- ChromaDB for local dev (zero infrastructure), pgvector for production
- Hybrid retrieval is always on by default; pure-semantic available via config

> See [`docs/architecture.md`](../docs/architecture.md) and [`docs/ai-concepts.md`](../docs/ai-concepts.md) for pipeline diagrams.
