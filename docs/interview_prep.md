# Aurenix AI — Comprehensive Technical Interview Preparation Guide

This guide provides concise, interview-ready answers covering the **16 core technical domains** of Aurenix AI, derived directly from actual codebase implementations.

---

### 1. Architecture Questions

**Q: Can you explain the high-level architecture of Aurenix AI?**  
**A:** Aurenix AI is a full-stack, enterprise-grade AI assistant. The backend is built with asynchronous **FastAPI (Python 3.11)**, structured in a modular service layer (LLM Gateway, RAG Engine, LangGraph Agents, Memory Service, Ingestion Pipeline, MCP Registry). The database layer uses **PostgreSQL 15** for relational persistence and **Qdrant** for vector similarity search. The frontend is a responsive **Next.js 16 (React 19, TypeScript)** application utilizing Tailwind CSS and SSE for real-time token streaming.

---

### 2. RAG Questions

**Q: How is the RAG pipeline designed in Aurenix AI?**  
**A:** When a user queries a workspace, the query first passes through an intent pre-processor that detects basic greetings to fast-path responses without unnecessary vector searches. Informational queries are embedded via `text-embedding-3-small` (checking an in-memory SHA-256 LRU cache first) and retrieved from Qdrant with mandatory `workspace_id` filtering. Chunks are deduplicated using a 20-token sliding key, capped by a character budget (`max_context_chars=8000`), and formatted into numbered `Document [X]` citations for grounded LLM generation.

---

### 3. LLM Questions

**Q: How does Aurenix AI handle LLM provider abstraction, retries, and errors?**  
**A:** All LLM interactions route through an `LLMService` supporting OpenAI, Anthropic, and deterministic Mock providers. It implements exponential backoff retries with jitter for rate limits (429) and timeouts, structured JSON schema outputs via Pydantic, and automatic secret redaction in all logging layers.

---

### 4. Embedding Questions

**Q: How are text embeddings generated and optimized in Aurenix AI?**  
**A:** Embeddings use OpenAI's 1536-dimensional `text-embedding-3-small`. To minimize API costs and latency, `EmbeddingService` is fronted by a thread-safe LRU `EmbeddingCache` keyed by `SHA-256(provider:model:text)`. Cache hits return in `< 0.02ms` with zero token cost. Batch embedding lookups partition cached vs uncached chunks to minimize upstream batch payloads.

---

### 5. Vector Database Questions

**Q: Why was Qdrant chosen and how is multi-tenancy enforced?**  
**A:** Qdrant was selected for its high-performance Rust core, native payload filtering, and async Python SDK. Multi-tenancy is enforced by creating payload indexes on `workspace_id` and requiring a strict boolean `must` filter on every vector search query, ensuring complete cryptographic separation between workspace tenants in a single shared collection (`aurenix_documents` and `aurenix_memories`).

---

### 6. Agent Questions

**Q: How are autonomous agents designed in Aurenix AI?**  
**A:** Agents are modeled as state machines using LangGraph. Each agent coordinates planning, tool reasoning, tool execution, and synthesis steps. Agents operate with a maximum recursion depth limit (10 steps) to prevent runaway loops and enforce structured fallback degradation.

---

### 7. LangGraph Questions

**Q: How is LangGraph utilized specifically in the codebase?**  
**A:** We use LangGraph's `StateGraph` with a strongly typed `AgentState` schema holding messages, scratchpads, step counters, and memory context. Conditional edges route between direct response generation, RAG document search, and tool execution nodes based on parsed tool call decisions.

---

### 8. Tool Calling Questions

**Q: How does the tool execution sandbox work?**  
**A:** Tools are registered in a centralized `ToolRegistry` with JSON Schema parameter definitions. When an agent requests a tool call, inputs are validated against the schema, checked against permissions, executed asynchronously with timeout guards (e.g. 10s), and failures are wrapped in structured `ToolExecutionError` envelopes.

---

### 9. MCP (Model Context Protocol) Questions

**Q: How does Aurenix AI integrate with the Model Context Protocol?**  
**A:** Aurenix AI includes an MCP Client (`app/services/mcp/`) that connects to external MCP servers over Stdio or SSE transports using standard JSON-RPC 2.0. It supports dynamic tool discovery (`tools/list`), administrative tool allowlisting, and secure sandboxed invocation.

---

### 10. Memory Questions

**Q: What is the dual-tier memory system in Aurenix AI?**  
**A:** Tier 1 is an ephemeral dialogue message buffer stored in PostgreSQL for sliding conversational context. Tier 2 is a persistent semantic knowledge layer: after conversation turns, an LLM structured extractor identifies durable user/workspace facts, stores them in PostgreSQL (`Memory` model), and indexes them in Qdrant (`aurenix_memories`) for semantic retrieval across future conversations.

---

### 11. Security Questions

**Q: What security and defense-in-depth measures are implemented?**  
**A:** Authentication via JWT (HS256) and SHA-256 hashed API keys; RBAC with 4 roles (Owner, Admin, Member, Viewer); automated regex secret sanitization masking API keys in logs; sliding window token-bucket rate limiting (120 req/min); strict CORS origin validation; and immutable audit logging for enterprise compliance.

---

### 12. FastAPI Questions

**Q: How is FastAPI structured and configured for production?**  
**A:** FastAPI is structured using an application factory (`create_app`), modular APIRouters, unified Pydantic response envelopes (`ApiResponse[T]` and `ErrorResponse`), custom ASGI middleware (Request Logging and Rate Limiting), async lifespan context managers for database initialization, and standardized OpenAPI schemas.

---

### 13. PostgreSQL Questions

**Q: How are relational data and migrations managed in PostgreSQL?**  
**A:** Relational models are built with SQLAlchemy 2.0 async ORM (`AsyncEngine` with asyncpg driver). Connection pooling is hardened (`pool_size=20`, `max_overflow=10`, `pool_recycle=1800s`, `pool_pre_ping=True`). Database migrations are version-controlled and automated using **Alembic**.

---

### 14. Docker Questions

**Q: How are Docker containers optimized for production?**  
**A:** Backend uses a minimal multi-stage `python:3.11-slim` image using `uv` and runs under an unprivileged `appuser`. Frontend uses a multi-stage `node:20-alpine` build with Next.js standalone output (`output: 'standalone'`), resulting in a tiny production image footprint. `docker-compose.prod.yml` isolates databases in private internal networks with health checks.

---

### 15. Deployment Questions

**Q: What is the recommended production deployment architecture?**  
**A:** A containerized deployment on AWS ECS / GCP Cloud Run or VPS behind an Nginx reverse proxy / Cloudflare TLS termination. PostgreSQL is managed via RDS or Cloud SQL, Qdrant is hosted on persistent SSD volumes, and application containers run multi-worker Uvicorn instances (`--workers 4`).

---

### 16. Evaluation Questions

**Q: How do you evaluate and benchmark the RAG system?**  
**A:** We built an automated evaluation framework (`evaluation/`) benchmarked against 12 enterprise multi-domain scenarios. It measures **Hit Rate (1.0)**, **Precision@K (1.0)**, **Recall@K (1.0)**, **MRR (1.0)**, **Answer Relevance (1.0)**, **Faithfulness/Grounding (0.917)**, **Citation Correctness (0.875)**, and latency telemetry (Retrieval: 4.2ms, End-to-End: 124.7ms).
