# backend/

FastAPI application — HTTP gateway, authentication, session management, and API routing.

**Planned Sprint:** Sprint 1

## Responsibilities

- JWT-based authentication and user management
- REST API and SSE streaming endpoints
- Request validation, middleware (CORS, rate limiting, logging)
- Database migrations via Alembic

## Structure (Sprint 1)

```
backend/
├── app/
│   ├── main.py           # FastAPI app factory with lifespan
│   ├── config.py         # Pydantic Settings (env-driven)
│   ├── auth/             # JWT, password hashing, token models
│   ├── routes/           # API route handlers
│   ├── middleware/        # CORS, structured logging, rate limiting
│   └── dependencies/     # DI providers (DB session, current user)
├── migrations/           # Alembic revisions
├── tests/
├── pyproject.toml
└── .env.example
```

## Key Design Decisions

- Async-first: all database calls use `asyncpg` / `SQLAlchemy async`
- Secrets via environment variables only — never hard-coded
- All endpoints return a consistent JSON envelope (see `docs/api-design.md`)

> See [`docs/architecture.md`](../docs/architecture.md) for full component specification.
