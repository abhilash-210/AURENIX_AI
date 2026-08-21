# Aurenix AI — Enterprise Retrieval-Augmented Generation (RAG) Architecture

> **Module:** `backend/app/services/rag/` & `backend/app/routes/rag.py`  
> **Status:** Production-Ready | Multi-Tenant Isolated | Benchmarked

---

## 1. RAG Pipeline Overview

The Aurenix AI RAG subsystem provides low-latency, context-grounded retrieval over ingested enterprise documents (PDF, DOCX, TXT, CSV, MD) with workspace scoping and citation tracking.

```
                      ┌──────────────────────────────────────┐
                      │          User Query Input            │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    1. Query Pre-Processing           │
                      │    • Regex Intent Detection          │
                      │    • Greeting Fast-Path Bypass       │
                      └──────────────────┬───────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │ (Greeting Detected)                       │ (Information Query)
                   ▼                                           ▼
      ┌─────────────────────────┐             ┌──────────────────────────────────┐
      │ Direct LLM Completion   │             │ 2. Query Embedding Generation    │
      │ (0 ms Vector Overhead)  │             │ • In-Memory LRU Hash Cache Check │
      └─────────────────────────┘             │ • text-embedding-3-small (1536d) │
                                              └────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                              ┌──────────────────────────────────┐
                                              │ 3. Qdrant Vector Retrieval       │
                                              │ • Filter: workspace_id == UUID   │
                                              │ • Metric: Cosine Similarity      │
                                              │ • Top-K: default 5               │
                                              └────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                              ┌──────────────────────────────────┐
                                              │ 4. Re-Ranking & Deduplication    │
                                              │ • 20-token sliding key filter    │
                                              │ • DummyReranker / Cross-Encoder  │
                                              └────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                              ┌──────────────────────────────────┐
                                              │ 5. Context & Citation Synthesis  │
                                              │ • max_context_chars (8,000 chars)│
                                              │ • Document [1], [2] tag mapping  │
                                              └────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                              ┌──────────────────────────────────┐
                                              │ 6. Grounded LLM Generation       │
                                              │ • Streaming SSE or JSON          │
                                              │ • Explicit Citation Attribution  │
                                              └──────────────────────────────────┘
```

---

## 2. Chunking & Ingestion Strategy

* **Supported File Types**: PDF (pypdf), DOCX (python-docx), TXT/MD (plain utf-8), CSV (row-aware chunking).
* **Chunk Parameters**: 
  * `chunk_size`: 500 tokens (approx 2,000 characters).
  * `chunk_overlap`: 50 tokens (approx 200 characters) to preserve contextual boundaries.
* **Payload Metadata**:
  * `document_id`: Database UUID.
  * `workspace_id`: Multi-tenant boundary.
  * `source_filename`: Original filename.
  * `page_number` / `row_number`: Exact provenance location.
  * `chunk_text`: Content snippet.

---

## 3. Vector Database Isolation & Indexing (Qdrant)

* **Collection Name**: `aurenix_documents` (Vector dimension: 1536).
* **Distance Metric**: Cosine Distance.
* **Multi-Tenant Filter**: Payload index on `workspace_id` (Keyword type). Queries strictly filter:
  ```json
  {
    "must": [
      { "key": "workspace_id", "match": { "value": "<WORKSPACE_UUID>" } }
    ]
  }
  ```

---

## 4. Groundedness & Anti-Hallucination Controls

1. **System Directive**: The LLM is instructed to answer strictly from the supplied `Document [X]` context snippets and state explicitly when documents do not contain the answer.
2. **Context Budgeting**: `ContextBuilder` enforces `max_context_chars=8000` to prevent context stuffing and token truncation.
3. **Automated Faithfulness Scoring**: Tested via `evaluation/metrics/faithfulness.py` achieving $> 0.91$ groundedness across benchmark datasets.
