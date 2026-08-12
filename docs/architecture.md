# Aurenix AI — System Architecture

> **Document Status:** Sprint 0 — Initial Design  
> **Last Updated:** 2026-08-12  
> **Audience:** Engineers, Technical Reviewers, Contributors

---

## Table of Contents

1. [Architectural Philosophy](#1-architectural-philosophy)
2. [System Context](#2-system-context)
3. [Component Breakdown](#3-component-breakdown)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [Technology Selections](#5-technology-selections)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Decision Log](#7-decision-log)

---

## 1. Architectural Philosophy

Aurenix AI is designed around five principles:

| Principle | Rationale |
|---|---|
| **Modularity** | Each subsystem (RAG, memory, agents, tools) is independently deployable and testable |
| **Observability-first** | Every component emits structured logs and trace IDs from day one |
| **Secrets hygiene** | Zero hard-coded credentials; all secrets via environment variables |
| **Incremental delivery** | Each sprint leaves the system in a working, demonstrable state |
| **Explicit over implicit** | Configuration is always declared, never inferred at runtime |

---

## 2. System Context

```
External Users
     │
     │  HTTPS / WSS
     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Aurenix AI Platform                    │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │   Frontend   │    │          Backend API             │  │
│  │  (Next.js)   │◄──►│           (FastAPI)              │  │
│  └──────────────┘    └──────┬──────────┬───────┬────────┘  │
│                             │          │       │           │
│               ┌─────────────▼──┐  ┌────▼───┐  ┌▼───────┐  │
│               │    Agents      │  │  RAG   │  │Memory  │  │
│               │  Orchestrator  │  │Pipeline│  │ Store  │  │
│               └───────┬────────┘  └────────┘  └────────┘  │
│                       │                                    │
│               ┌───────▼────────┐                           │
│               │  Tools Layer   │                           │
│               └────────────────┘                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Evaluation & Observability              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
  External LLM APIs                  Data Stores
  (OpenAI, Cohere, etc.)     (PostgreSQL, Redis, ChromaDB)
```

---

## 3. Component Breakdown

### 3.1 Backend (`backend/`)

**Responsibility:** HTTP/WebSocket gateway, authentication, session lifecycle, request routing.

- Framework: **FastAPI** (async, OpenAPI auto-generation, dependency injection)
- Auth: **JWT** with refresh token rotation
- Session: stateless API layer; session state lives in the memory module
- Transport: REST + Server-Sent Events (SSE) for token streaming

**Key sub-modules (planned):**
```
backend/
├── app/
│   ├── main.py           # FastAPI app factory
│   ├── config.py         # Pydantic Settings (env-driven)
│   ├── auth/             # JWT, user models, token handling
│   ├── routes/           # API route handlers
│   ├── middleware/        # CORS, logging, rate limiting
│   └── dependencies/     # DI providers (DB session, current user)
├── migrations/           # Alembic database migrations
└── tests/
```

---

### 3.2 Frontend (`frontend/`)

**Responsibility:** User-facing chat interface, document management, analytics dashboard.

- Framework: **Next.js 14** (App Router, React Server Components)
- Styling: **Tailwind CSS** + **shadcn/ui**
- State: **Zustand** for client state, **React Query** for server state
- Streaming: Native `EventSource` API for SSE consumption

---

### 3.3 Agents (`agents/`)

**Responsibility:** Multi-agent orchestration, reasoning, task decomposition.

- Topology: **Supervisor + Specialist** pattern
  - Supervisor routes incoming requests to the appropriate specialist
  - Specialists: Research Agent, Summarisation Agent, Q&A Agent, Code Agent
- Framework: **LangGraph** (stateful graph-based agent runtime)
- Prompt management: versioned system prompt templates per agent

**Execution flow:**
```
User Query
    │
    ▼
Supervisor Agent
    │ classify intent
    ▼
Specialist Agent ──► Tool Calls ──► Tool Results
    │
    ▼
Response + Citations
```

---

### 3.4 RAG Pipeline (`rag/`)

**Responsibility:** Document ingestion, embedding, retrieval, and answer generation.

**Ingestion pipeline:**
```
Raw Document (PDF / DOCX / TXT / URL)
    │
    ▼ Extraction
    │
    ▼ Chunking (recursive text splitter)
    │
    ▼ Embedding (OpenAI text-embedding-3-small / local)
    │
    ▼ Vector Store (ChromaDB or pgvector)
```

**Retrieval pipeline:**
```
User Query
    │
    ▼ Query embedding
    │
    ├──► Semantic search (cosine similarity, top-k)
    ├──► Keyword search (BM25)
    │
    ▼ Reciprocal Rank Fusion
    │
    ▼ Re-ranking (Cohere Rerank / cross-encoder)
    │
    ▼ Context assembly → LLM → Answer + Citations
```

---

### 3.5 Memory (`memory/`)

**Responsibility:** Multi-horizon context storage and retrieval across conversations.

| Layer | Storage | Scope | Retention |
|---|---|---|---|
| Short-term | Redis | Current conversation window | Session lifetime |
| Long-term | PostgreSQL | User-level persistent facts | Indefinite |
| Episodic | PostgreSQL | Timestamped interaction logs | Configurable |

---

### 3.6 Tools (`tools/`)

**Responsibility:** Pluggable capability extensions for agents.

- **Architecture:** Registry pattern — tools self-register via decorator
- **Interface:** Every tool exposes `name`, `description`, `input_schema`, `run()`
- **Planned tools:** Web search (Tavily), calculator, SQL query, file reader, code interpreter

---

### 3.7 Evaluation (`evaluation/`)

**Responsibility:** Automated quality assurance for LLM outputs.

- **Framework:** RAGAS (open-source RAG evaluation)
- **Metrics tracked:**
  - Faithfulness (answer grounded in retrieved context)
  - Answer Relevance (answer addresses the question)
  - Context Recall (retrieved context covers the answer)
  - Context Precision (retrieved context is not noisy)
  - Hallucination Rate (claims not supported by sources)

---

## 4. Data Flow Diagrams

### 4.1 Chat Request (with RAG)

```
Client → POST /api/v1/chat
    │
    ▼ Auth middleware (JWT validation)
    │
    ▼ Session service (load conversation history)
    │
    ▼ Supervisor Agent
    │    │
    │    ▼ RAG retrieval (if knowledge-base query)
    │    │
    │    ▼ Specialist Agent (LLM call + tool calls)
    │    │
    │    ▼ Response streaming (SSE)
    │
    ▼ Memory service (persist turn to short + long term)
    │
    ▼ Evaluation (async, non-blocking)
    │
Client ← stream of tokens + citations
```

---

## 5. Technology Selections

| Layer | Technology | Justification |
|---|---|---|
| Backend framework | FastAPI | Async-native, OpenAPI built-in, excellent DI system |
| Frontend framework | Next.js 14 | RSC, SSE support, Vercel-deployable |
| Agent runtime | LangGraph | Stateful graph execution, human-in-the-loop support |
| Embedding | OpenAI `text-embedding-3-small` | Cost-efficient, high quality; swappable |
| LLM | OpenAI GPT-4o | State-of-art reasoning; provider-agnostic via LiteLLM |
| Vector store | ChromaDB (dev) / pgvector (prod) | Simple local dev, scalable prod option |
| Relational DB | PostgreSQL 16 | ACID compliance, pgvector extension |
| Cache | Redis 7 | Fast short-term memory, pub/sub for streaming |
| Evaluation | RAGAS | Industry-standard RAG metrics |
| Containerisation | Docker Compose | Reproducible local environments |
| Package manager (Python) | uv | 10-100x faster than pip |
| Package manager (Node) | pnpm | Efficient disk usage, strict dependency resolution |

---

## 6. Cross-Cutting Concerns

### 6.1 Authentication & Authorization
- JWT access tokens (15 min expiry) + refresh tokens (7 days)
- Role-based access control (RBAC): `admin`, `user`, `readonly`
- Tenant scoping: all DB queries filter by `tenant_id`

### 6.2 Observability
- **Structured logging:** JSON logs with `trace_id`, `user_id`, `tenant_id`, `duration_ms`
- **Tracing:** OpenTelemetry spans for every agent step and tool call
- **Metrics:** Token usage, latency p50/p95/p99, error rates
- **LLM cost tracking:** Token counts logged per request

### 6.3 Error Handling
- Agents retry transient LLM errors with exponential backoff (max 3 attempts)
- Fallback responses when retrieval returns zero results
- Circuit breaker pattern for external tool calls

### 6.4 Security
- All secrets loaded from environment variables (never committed)
- Input sanitisation before any LLM prompt construction
- Rate limiting per user and per tenant
- CORS restricted to allowed origins in production

---

## 7. Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|---|---|---|
| ADR-001 | LangGraph over raw LangChain | Graph-based state machine is more explicit and testable | LangChain LCEL, custom orchestrator |
| ADR-002 | FastAPI over Django | Lightweight, async-first, minimal boilerplate | Django REST Framework, Flask |
| ADR-003 | pgvector in prod, ChromaDB in dev | Avoid dual storage systems at scale; pgvector keeps vectors co-located with relational data | Pinecone, Weaviate, Qdrant |
| ADR-004 | SSE over WebSocket for streaming | Simpler protocol, HTTP/2 compatible, sufficient for unidirectional token streams | WebSocket, long-polling |
| ADR-005 | Monorepo over poly-repo | Atomic cross-module commits, easier local development | Separate repos per service |
| ADR-006 | uv over pip/poetry | 10-100x faster resolution and installation, lock-file based | pip + requirements.txt, Poetry, Pipenv |
