# Aurenix AI — API Design

> **Document Status:** Sprint 0 — Design Phase  
> **Last Updated:** 2026-08-12  
> **Base URL:** `https://api.aurenix.ai/api/v1` (production)  
> **Local Dev:** `http://localhost:8000/api/v1`

> [!NOTE]
> This document defines the **intended API contract** for Sprint 1 onwards. Endpoints marked `[Sprint N]` will be implemented in that sprint. No endpoints exist yet.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Authentication](#2-authentication)
3. [Common Conventions](#3-common-conventions)
4. [Endpoints — Health](#4-endpoints--health)
5. [Endpoints — Auth](#5-endpoints--auth)
6. [Endpoints — Chat](#6-endpoints--chat)
7. [Endpoints — Documents](#7-endpoints--documents)
8. [Endpoints — Retrieval](#8-endpoints--retrieval)
9. [Endpoints — Memory](#9-endpoints--memory)
10. [Endpoints — Evaluation](#10-endpoints--evaluation)
11. [Error Schema](#11-error-schema)
12. [Versioning Policy](#12-versioning-policy)

---

## 1. Design Principles

| Principle | Implementation |
|---|---|
| RESTful resources | Nouns in paths, HTTP verbs for actions |
| Consistent error schema | All errors follow the same JSON envelope |
| Versioned routes | `/api/v1/` prefix on all endpoints |
| JSON everywhere | All request and response bodies are `application/json` |
| Streaming via SSE | Long-running responses use `text/event-stream` |
| Authenticated by default | All endpoints require JWT unless explicitly marked `[Public]` |
| Idempotent where possible | `PUT` and `DELETE` are safe to retry |

---

## 2. Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Token lifecycle

```
POST /auth/register  → { access_token, refresh_token }
POST /auth/login     → { access_token, refresh_token }
POST /auth/refresh   → { access_token }              (uses refresh_token)
POST /auth/logout    → 204 No Content                (revokes refresh_token)
```

- **Access token:** JWT, expires in 15 minutes
- **Refresh token:** Opaque, stored in HttpOnly cookie, expires in 7 days
- **Rotation:** A new refresh token is issued on every `/auth/refresh` call

---

## 3. Common Conventions

### Pagination

All list endpoints support cursor-based pagination:

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true,
    "limit": 20
  }
}
```

Query parameters: `?limit=20&cursor=<next_cursor>`

### Timestamps

All timestamps are **ISO 8601 UTC**:  
`"created_at": "2026-08-12T17:00:00Z"`

### IDs

All resource IDs are **UUID v4** strings.

### Envelope

Successful responses:
```json
{
  "data": { ... },
  "meta": { "request_id": "uuid", "duration_ms": 42 }
}
```

---

## 4. Endpoints — Health

### `GET /health` `[Public]` `[Sprint 1]`

Returns service health. No authentication required.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-08-12T17:00:00Z",
  "services": {
    "database": "ok",
    "redis": "ok",
    "vector_store": "ok"
  }
}
```

---

## 5. Endpoints — Auth

### `POST /auth/register` `[Public]` `[Sprint 1]`

Create a new user account.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "Alex Jordan"
}
```

**Response `201 Created`:**
```json
{
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "full_name": "Alex Jordan",
    "created_at": "2026-08-12T17:00:00Z"
  },
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### `POST /auth/login` `[Public]` `[Sprint 1]`

Authenticate and receive tokens.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response `200 OK`:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```
*Refresh token set as `HttpOnly` cookie.*

---

### `POST /auth/refresh` `[Sprint 1]`

Exchange a refresh token for a new access token.

**Request:** No body. Refresh token read from `HttpOnly` cookie.

**Response `200 OK`:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### `POST /auth/logout` `[Sprint 1]`

Revoke the current refresh token.

**Response `204 No Content`**

---

### `GET /auth/me` `[Sprint 1]`

Get the currently authenticated user.

**Response `200 OK`:**
```json
{
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "full_name": "Alex Jordan",
    "role": "user",
    "created_at": "2026-08-12T17:00:00Z"
  }
}
```

---

## 6. Endpoints — Chat

### `POST /chat/sessions` `[Sprint 3]`

Create a new chat session.

**Request body:**
```json
{
  "title": "Q3 Budget Analysis"
}
```

**Response `201 Created`:**
```json
{
  "data": {
    "session_id": "uuid",
    "title": "Q3 Budget Analysis",
    "created_at": "2026-08-12T17:00:00Z"
  }
}
```

---

### `GET /chat/sessions` `[Sprint 3]`

List all sessions for the current user.

**Query params:** `?limit=20&cursor=<cursor>`

**Response `200 OK`:**
```json
{
  "data": [
    {
      "session_id": "uuid",
      "title": "Q3 Budget Analysis",
      "last_message_at": "2026-08-12T17:00:00Z",
      "message_count": 12
    }
  ],
  "pagination": { "next_cursor": null, "has_more": false, "limit": 20 }
}
```

---

### `POST /chat/sessions/{session_id}/messages` `[Sprint 3]`

Send a message and receive a **streaming** response via SSE.

**Request body:**
```json
{
  "content": "What was our Q3 revenue?",
  "agent": "research"
}
```

**Response `200 OK` — `Content-Type: text/event-stream`:**
```
data: {"type": "token", "content": "Based"}
data: {"type": "token", "content": " on"}
data: {"type": "token", "content": " the"}
...
data: {"type": "citation", "source": "Q3_Report.pdf", "chunk_id": "uuid", "page": 4}
data: {"type": "done", "message_id": "uuid", "usage": {"prompt_tokens": 512, "completion_tokens": 128}}
```

---

### `GET /chat/sessions/{session_id}/messages` `[Sprint 3]`

Retrieve message history for a session.

**Response `200 OK`:**
```json
{
  "data": [
    {
      "message_id": "uuid",
      "role": "user",
      "content": "What was our Q3 revenue?",
      "created_at": "2026-08-12T17:00:00Z"
    },
    {
      "message_id": "uuid",
      "role": "assistant",
      "content": "Based on the Q3 report...",
      "citations": [
        { "source": "Q3_Report.pdf", "chunk_id": "uuid", "page": 4 }
      ],
      "created_at": "2026-08-12T17:00:10Z"
    }
  ]
}
```

---

## 7. Endpoints — Documents

### `POST /documents/ingest` `[Sprint 2]`

Upload and ingest a document into the knowledge base.

**Request:** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `file` | binary | PDF, DOCX, or TXT file |
| `title` | string | Human-readable document title |
| `collection` | string | Knowledge base collection name |

**Response `202 Accepted`:**
```json
{
  "data": {
    "document_id": "uuid",
    "title": "Q3 Financial Report",
    "status": "processing",
    "created_at": "2026-08-12T17:00:00Z"
  }
}
```

---

### `GET /documents` `[Sprint 2]`

List all documents in the knowledge base.

**Response `200 OK`:**
```json
{
  "data": [
    {
      "document_id": "uuid",
      "title": "Q3 Financial Report",
      "status": "ready",
      "chunk_count": 47,
      "created_at": "2026-08-12T17:00:00Z"
    }
  ]
}
```

---

### `GET /documents/{document_id}` `[Sprint 2]`

Get details and ingestion status for a specific document.

**Response `200 OK`:**
```json
{
  "data": {
    "document_id": "uuid",
    "title": "Q3 Financial Report",
    "status": "ready",
    "chunk_count": 47,
    "file_size_bytes": 204800,
    "collection": "finance",
    "created_at": "2026-08-12T17:00:00Z"
  }
}
```

---

### `DELETE /documents/{document_id}` `[Sprint 2]`

Delete a document and all its chunks from the vector store.

**Response `204 No Content`**

---

## 8. Endpoints — Retrieval

### `POST /retrieval/query` `[Sprint 2]`

Run a retrieval query against the knowledge base (without LLM generation).

**Request body:**
```json
{
  "query": "What was Q3 net revenue?",
  "collection": "finance",
  "top_k": 5,
  "retrieval_mode": "hybrid"
}
```

**Response `200 OK`:**
```json
{
  "data": {
    "chunks": [
      {
        "chunk_id": "uuid",
        "document_id": "uuid",
        "document_title": "Q3 Financial Report",
        "content": "Q3 net revenue was $4.2M, up 18% YoY...",
        "score": 0.94,
        "page": 4
      }
    ],
    "retrieval_mode": "hybrid",
    "latency_ms": 87
  }
}
```

---

## 9. Endpoints — Memory

### `GET /memory/{session_id}` `[Sprint 4]`

Retrieve the short-term memory for a session.

**Response `200 OK`:**
```json
{
  "data": {
    "session_id": "uuid",
    "turns": [
      { "role": "user", "content": "...", "timestamp": "..." },
      { "role": "assistant", "content": "...", "timestamp": "..." }
    ],
    "long_term_facts": [
      { "fact": "User prefers tabular output", "confidence": 0.9 }
    ]
  }
}
```

---

### `DELETE /memory/{session_id}` `[Sprint 4]`

Clear short-term memory for a session.

**Response `204 No Content`**

---

## 10. Endpoints — Evaluation

### `GET /evaluation/report` `[Sprint 6]`

Get aggregate evaluation metrics.

**Query params:** `?from=2026-08-01&to=2026-08-12&metric=faithfulness`

**Response `200 OK`:**
```json
{
  "data": {
    "period": { "from": "2026-08-01", "to": "2026-08-12" },
    "metrics": {
      "faithfulness": { "mean": 0.87, "p50": 0.91, "p10": 0.62 },
      "answer_relevance": { "mean": 0.82, "p50": 0.85, "p10": 0.55 },
      "context_precision": { "mean": 0.79, "p50": 0.83, "p10": 0.48 },
      "hallucination_rate": { "mean": 0.04 }
    },
    "total_evaluations": 1247
  }
}
```

---

## 11. Error Schema

All errors return a consistent JSON envelope:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Access token is expired or invalid.",
    "request_id": "uuid",
    "timestamp": "2026-08-12T17:00:00Z"
  }
}
```

### Error codes

| HTTP Status | Code | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body failed schema validation |
| 401 | `UNAUTHORIZED` | Missing or invalid access token |
| 403 | `FORBIDDEN` | Token valid but insufficient permissions |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Resource already exists (e.g., duplicate email) |
| 422 | `UNPROCESSABLE` | Semantically invalid input |
| 429 | `RATE_LIMITED` | Too many requests; retry after `Retry-After` header |
| 500 | `INTERNAL_ERROR` | Unexpected server error; check `request_id` in logs |
| 503 | `SERVICE_UNAVAILABLE` | Dependency (LLM, DB) is temporarily unavailable |

---

## 12. Versioning Policy

- The current API version is **v1**, reflected in the base path `/api/v1/`.
- **Breaking changes** (removed fields, changed semantics) increment the version: `/api/v2/`.
- **Additive changes** (new optional fields, new endpoints) are non-breaking and do not require version increment.
- Deprecated endpoints are announced via a `Deprecation` response header with a sunset date, giving consumers 90 days to migrate.
