<div align="center">

<br/>

# ✦ Aurenix AI

### Enterprise Intelligence Operating System

*Modular · Agentic · Production-Grade*

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-6C63FF.svg)](LICENSE)
[![Status: Sprint 0](https://img.shields.io/badge/Status-Sprint%200%20%E2%80%94%20Architecture-orange.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)]()
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg)]()

</div>

---

## Vision

Aurenix AI is a production-inspired **Enterprise Intelligence Operating System** — a unified platform that orchestrates autonomous AI agents, retrieval-augmented generation pipelines, persistent memory, and enterprise tooling into a single, composable runtime.

It is designed to demonstrate how modern, modular AI systems are built at scale: not as a monolithic chatbot, but as a coordinated ecosystem of intelligent, observable, and governable components.

---

## Problem Statement

Most AI demonstrations are either:

- **Too simple** — a single LLM call wrapped in a REST endpoint.
- **Too opaque** — a black box that cannot be audited, traced, or improved.
- **Too brittle** — hard-coded prompts with no memory, no tools, and no fallback.

Enterprise teams building real AI products face a fundamentally different challenge: they need agents that can **reason across data sources**, **remember context across sessions**, **call real tools**, **evaluate their own outputs**, and **fail gracefully**.

Aurenix AI is the reference architecture that closes that gap.

---

## Planned Capabilities

| Capability | Description |
|---|---|
| 🤖 **Multi-Agent Orchestration** | Supervisor + specialist agent topology with structured handoffs |
| 🔍 **Retrieval-Augmented Generation** | Hybrid vector + keyword search over enterprise knowledge bases |
| 🧠 **Persistent Memory** | Short-term, long-term, and episodic memory layers across sessions |
| 🛠️ **Tool Integration** | Pluggable tool registry for APIs, databases, calculators, and web search |
| 📊 **Evaluation Framework** | Automated quality scoring — faithfulness, relevance, hallucination rate |
| 🔐 **Auth & Multi-Tenancy** | JWT-based auth with tenant-scoped data isolation |
| 📡 **Streaming Responses** | Server-Sent Events for real-time token streaming to the UI |
| 🗂️ **Conversation Management** | Full session history, branching, and replay |
| 📈 **Observability** | Structured logging, trace IDs, and LLM cost tracking |
| 🚀 **Production Deployment** | Containerized via Docker Compose with environment-based configuration |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                   │
│            Chat UI · Dashboard · Document Viewer            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                  Backend API (FastAPI)                       │
│        Auth · Session Management · Streaming Gateway        │
└──────┬─────────────────┬──────────────────┬─────────────────┘
       │                 │                  │
┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│   Agents    │  │     RAG      │  │    Memory    │
│  Supervisor │  │  Retrieval + │  │  Short/Long  │
│  Specialist │  │  Generation  │  │  Episodic    │
└──────┬──────┘  └───────┬──────┘  └───────┬──────┘
       │                 │                  │
┌──────▼─────────────────▼──────────────────▼──────┐
│                     Tools Layer                   │
│   Web Search · Calculator · DB Query · File I/O  │
└──────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│              Evaluation & Observability                     │
│        Faithfulness · Relevance · Cost · Latency            │
└─────────────────────────────────────────────────────────────┘
```

For the complete architecture specification, see [`docs/architecture.md`](docs/architecture.md).

---

## Repository Structure

```
aurenix-ai/
├── backend/         # FastAPI application — auth, sessions, API gateway
├── frontend/        # Next.js application — chat UI and dashboard
├── agents/          # Agent definitions, supervisor, and specialist prompts
├── rag/             # Document ingestion, chunking, embedding, retrieval
├── memory/          # Short-term, long-term, and episodic memory modules
├── tools/           # Pluggable tool registry and individual tool adapters
├── evaluation/      # Automated evaluation harness and metrics
├── tests/           # Unit, integration, and end-to-end test suites
├── docs/            # Architecture, roadmap, and API design documentation
├── deployment/      # Docker Compose, Kubernetes manifests, env templates
├── scripts/         # Developer utility scripts (setup, seed, lint, test)
├── .github/         # CI/CD workflows and issue/PR templates
├── .gitignore
├── README.md
└── LICENSE
```

---

## Technology Roadmap

### Sprint 0 — Foundation *(current)*
- Repository structure and documentation scaffold
- Architecture decisions and technology selections
- Development standards and contribution guidelines

### Sprint 1 — Backend Core
- FastAPI application skeleton with health endpoint
- JWT authentication and user model
- PostgreSQL database schema and migrations (Alembic)
- Docker Compose for local development

### Sprint 2 — RAG Pipeline
- Document ingestion and chunking pipeline
- Embedding generation via OpenAI / local model
- Vector store integration (ChromaDB / pgvector)
- Hybrid retrieval with BM25 + semantic search

### Sprint 3 — Agent Orchestration
- LangGraph-based supervisor agent
- Specialist agents (research, summarisation, Q&A)
- Tool registry with web search and calculator adapters
- Streaming response gateway

### Sprint 4 — Memory System
- Redis-backed short-term (conversation) memory
- PostgreSQL long-term memory with summarisation
- Episodic memory with timestamp and relevance scoring

### Sprint 5 — Frontend
- Next.js 14 App Router chat interface
- Real-time streaming via SSE
- Document upload and knowledge base management UI
- Admin dashboard with usage analytics

### Sprint 6 — Evaluation & Observability
- RAGAS-based evaluation framework integration
- Faithfulness, relevance, and groundedness metrics
- Structured logging with trace IDs
- OpenTelemetry integration

### Sprint 7 — Production Hardening
- Multi-tenancy and data isolation
- Rate limiting and cost controls
- Kubernetes manifests and Helm chart
- CI/CD pipeline with automated testing

---

## Development Methodology

Aurenix AI is built using an **incremental sprint methodology**:

1. **Every sprint delivers a working, testable increment** — no placeholder code.
2. **Each module is independently testable** before integration.
3. **Architecture decisions are documented** before implementation begins.
4. **Environment variables govern all secrets** — no hard-coded credentials.
5. **CI enforces linting, type-checking, and tests** on every pull request.

---

## Local Development Prerequisites

Before cloning and running Aurenix AI, ensure the following are installed:

| Tool | Version | Purpose |
|---|---|---|
| [Python](https://python.org) | 3.11+ | Backend runtime |
| [Node.js](https://nodejs.org) | 20 LTS | Frontend runtime |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Latest | Container orchestration |
| [Git](https://git-scm.com) | 2.40+ | Version control |
| [pnpm](https://pnpm.io) | 8+ | Node package manager |
| [uv](https://github.com/astral-sh/uv) | Latest | Fast Python package manager |

> **API Keys Required (later sprints):** OpenAI API key (or compatible provider), optional: Cohere, Tavily (web search).

---

## Documentation

| Document | Description |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, component responsibilities, data flows |
| [`docs/development-roadmap.md`](docs/development-roadmap.md) | Sprint plan with acceptance criteria |
| [`docs/ai-concepts.md`](docs/ai-concepts.md) | RAG, agents, memory, and evaluation explained |
| [`docs/api-design.md`](docs/api-design.md) | REST API contract and endpoint specifications |

---

## Contributing

This project follows a structured sprint process. To contribute:

1. Fork the repository.
2. Create a branch: `git checkout -b sprint-N/your-feature`.
3. Commit with a conventional message: `feat(rag): add chunking pipeline`.
4. Push and open a Pull Request against `main`.

See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for the full guide.

---

## License

Distributed under the [MIT License](LICENSE). See `LICENSE` for full terms.

---

<div align="center">

*Built with intentionality. Architected for production. Documented for learning.*

**Aurenix AI** · Sprint 0

</div>
