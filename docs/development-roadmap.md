# Aurenix AI — Development Roadmap

> **Document Status:** Sprint 0 — Initial Planning  
> **Last Updated:** 2026-08-12  
> **Methodology:** Incremental Sprint Delivery

---

## Overview

Each sprint delivers a **working, testable increment** of the system. No sprint ends with placeholder code. Every feature must be verifiable before the sprint is considered complete.

---

## Sprint 0 — Foundation & Architecture *(current)*

**Goal:** Establish the repository, document the system, and align on all architectural decisions before writing production code.

**Deliverables:**

| Item | Status |
|---|---|
| Repository structure scaffolded | ✅ |
| `.gitignore` configured for Python, Node, Docker, secrets | ✅ |
| `README.md` with vision, problem statement, capabilities | ✅ |
| `docs/architecture.md` — system design and ADRs | ✅ |
| `docs/development-roadmap.md` — this document | ✅ |
| `docs/ai-concepts.md` — RAG, agents, memory explained | ✅ |
| `docs/api-design.md` — REST API contract | ✅ |
| GitHub CI/CD workflow stub | ✅ |
| Issue and PR templates | ✅ |
| CONTRIBUTING guide | ✅ |

**Acceptance Criteria:**
- [ ] Repository clones cleanly with no errors
- [ ] All documentation is internally consistent
- [ ] Architecture decisions are recorded in ADR log
- [ ] No production code exists yet (intentional)

---

## Sprint 1 — Backend Core

**Goal:** A running FastAPI server with authentication, health check, and database connectivity.

**Deliverables:**

| Item | Description |
|---|---|
| FastAPI app factory | `backend/app/main.py` with lifespan management |
| Environment configuration | Pydantic `Settings` class reading from `.env` |
| Health endpoint | `GET /api/v1/health` returns service status |
| User model | SQLAlchemy model + Alembic migration |
| JWT auth | Register, login, refresh, logout endpoints |
| Docker Compose | PostgreSQL + Redis + backend service |
| Unit tests | Auth logic tested in isolation |

**Acceptance Criteria:**
- [ ] `docker compose up` starts all services
- [ ] `POST /api/v1/auth/register` creates a user
- [ ] `POST /api/v1/auth/login` returns JWT pair
- [ ] `GET /api/v1/health` returns `{"status": "ok"}`
- [ ] All tests pass: `pytest backend/tests/`

---

## Sprint 2 — RAG Pipeline

**Goal:** Documents can be ingested, embedded, stored, and retrieved with citations.

**Deliverables:**

| Item | Description |
|---|---|
| Document loader | PDF, DOCX, TXT, plain URL ingestion |
| Text chunker | Recursive splitter with configurable chunk size / overlap |
| Embedding service | OpenAI `text-embedding-3-small` (env-switchable) |
| Vector store | ChromaDB for development |
| Retrieval service | Semantic search returning top-k chunks + metadata |
| BM25 hybrid search | Keyword retrieval fused with semantic via RRF |
| Ingestion API | `POST /api/v1/documents/ingest` |
| Retrieval API | `POST /api/v1/retrieval/query` |
| Unit tests | Chunking, embedding mock, retrieval ranking |

**Acceptance Criteria:**
- [ ] A PDF can be ingested and chunked correctly
- [ ] A query returns relevant chunks with source metadata
- [ ] Retrieval latency < 500 ms for a 1,000-document corpus
- [ ] All tests pass: `pytest rag/tests/`

---

## Sprint 3 — Agent Orchestration

**Goal:** A supervisor agent can route queries, call tools, and stream responses.

**Deliverables:**

| Item | Description |
|---|---|
| LangGraph supervisor | Intent classification and agent routing graph |
| Research agent | Uses RAG retrieval + web search |
| Q&A agent | Answers from retrieved context with citations |
| Summarisation agent | Condenses long documents or conversation history |
| Tool registry | Decorator-based self-registration pattern |
| Web search tool | Tavily API adapter |
| Calculator tool | Safe expression evaluator |
| Streaming gateway | SSE endpoint: `POST /api/v1/chat/stream` |
| Unit tests | Each agent tested with mocked LLM responses |

**Acceptance Criteria:**
- [ ] A query is routed to the correct specialist agent
- [ ] Tool calls are logged with input/output
- [ ] Tokens stream to client in < 200 ms first-token latency
- [ ] All tests pass: `pytest agents/tests/`

---

## Sprint 4 — Document Ingestion Pipeline

**Goal:** Documents can be securely uploaded, validated, parsed, and chunked with metadata.

**Deliverables:**

| Item | Description | Status |
|---|---|---|
| File validation | Secure validation, max size, sanitization | ✅ |
| Format Parsers | PDF, DOCX, TXT, CSV parsers | ✅ |
| Text Extraction & Cleaning | Extracts text, cleans control chars and whitespace | ✅ |
| Recursive Chunker | Chunks text preserving page/row/source metadata | ✅ |
| Storage Layer | Workspace association and file persistence | ✅ |
| Clean Interfaces | Defines ParsedDocument/ParsedPage for future vector layer | ✅ |
| Unit tests | Validation, parsing, and chunking tested with invalid files | ✅ |

**Acceptance Criteria:**
- [x] Secure file validation and configurable max size
- [x] Safe filenames and document ownership tracking
- [x] Parsers correctly handle PDF, DOCX, TXT, CSV formats
- [x] Chunker accurately splits text and adds page number / chunk metadata
- [x] All tests pass: `pytest backend/tests/test_document_*.py`

---

## Sprint 5 — Frontend

**Goal:** A production-quality chat interface with streaming and document management.

**Deliverables:**

| Item | Description |
|---|---|
| App shell | Next.js 14 App Router layout with sidebar |
| Authentication UI | Login, register, logout with JWT handling |
| Chat interface | Message thread, input box, streaming token rendering |
| Citation panel | Displays source chunks for each assistant response |
| Document manager | Upload, list, delete knowledge base documents |
| Session history | Sidebar list of past conversations |
| Responsive design | Mobile-first, works on tablet and desktop |

**Acceptance Criteria:**
- [ ] Login → chat → receive streamed response (end-to-end)
- [ ] Citations are displayed and link to source chunks
- [ ] App is accessible (WCAG AA colour contrast)
- [ ] Lighthouse performance score > 85

---

## Sprint 6 — Evaluation & Observability

**Goal:** Every LLM response is automatically scored; system health is fully observable.

**Deliverables:**

| Item | Description |
|---|---|
| RAGAS integration | Async evaluation of faithfulness, relevance, precision, recall |
| Evaluation storage | Scores persisted to PostgreSQL evaluation table |
| Evaluation API | `GET /api/v1/evaluation/report` — aggregate metrics |
| Structured logging | JSON logs with `trace_id`, `latency_ms`, `token_count` |
| OpenTelemetry | Spans for agent steps, retrieval, LLM calls |
| Cost tracker | Token usage logged per user and tenant |

**Acceptance Criteria:**
- [ ] Every response has a faithfulness score stored
- [ ] Logs are parseable JSON with required fields
- [ ] A weekly evaluation report can be generated from stored data

---

## Sprint 7 — Production Hardening

**Goal:** The system is deployable to a real cloud environment with security and scalability controls.

**Deliverables:**

| Item | Description |
|---|---|
| Multi-tenancy | All queries scoped by `tenant_id` |
| Rate limiting | Per-user and per-tenant token/request limits |
| pgvector migration | Vector store moved from ChromaDB to PostgreSQL pgvector |
| Kubernetes manifests | Deployment, Service, ConfigMap, Secret for all services |
| Helm chart | Parameterised chart for multi-environment deployment |
| GitHub Actions CI | Lint + test + build on every PR |
| GitHub Actions CD | Deploy to staging on merge to `main` |
| Security audit | Secrets scanning, SAST, dependency vulnerability check |

**Acceptance Criteria:**
- [ ] System deploys to a cloud Kubernetes cluster
- [ ] Tenant A cannot access Tenant B's data
- [ ] CI passes on all PRs
- [ ] No high/critical CVEs in dependency scan

---

## Velocity & Estimation

| Sprint | Estimated Duration | Complexity |
|---|---|---|
| 0 — Foundation | 1–2 days | Low |
| 1 — Backend Core | 3–5 days | Medium |
| 2 — RAG Pipeline | 4–6 days | High |
| 3 — Agent Orchestration | 5–7 days | High |
| 4 — Memory System | 3–4 days | Medium |
| 5 — Frontend | 4–6 days | Medium |
| 6 — Evaluation | 2–3 days | Medium |
| 7 — Production Hardening | 4–5 days | High |

> Estimates assume a single experienced developer. Team size scales velocity linearly.

---

## Definition of Done (Global)

A sprint is **done** when:

1. All listed deliverables exist and are non-placeholder.
2. All acceptance criteria pass.
3. New code has > 70% unit test coverage.
4. No secrets are committed to the repository.
5. All new endpoints are documented in `docs/api-design.md`.
6. A commit is tagged with the sprint number (e.g., `v0.1.0-sprint-1`).
