# Aurenix AI — Dual-Tier Semantic & Conversation Memory Subsystem

> **Module:** `backend/app/services/memory/` & `backend/app/models/memory.py`  
> **Status:** Production-Ready | Multi-Tier Scoped (User & Workspace)

---

## 1. Memory Architecture Overview

Aurenix AI implements a **dual-tier memory architecture** that separates ephemeral conversational dialogue state from long-term extracted semantic facts.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AURENIX AI MEMORY LIFECYCLE                           │
├───────────────────────────────────────┬─────────────────────────────────────────┤
│ Tier 1: Ephemeral Dialogue Buffer     │ Tier 2: Persistent Semantic Knowledge   │
├───────────────────────────────────────┼─────────────────────────────────────────┤
│ • Stored in PostgreSQL (Message table)│ • Stored in PostgreSQL + Qdrant Vectors │
│ • Windowed sliding history (N turns)  │ • Fact Extraction via Structured LLM    │
│ • Session-isolated per conversation   │ • Scoped by User ID or Workspace ID     │
│ • Fast retrieval by timestamp         │ • Semantic vector search across turns   │
└───────────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 2. Memory Extraction Lifecycle

```
[Chat Turn Complete]
        │
        ▼
[Background Fact Extractor] (LLM Structured Output)
        │
        ├── No new durable facts? ────────► [Discard (0 DB writes)]
        │
        ▼
[Durable Fact Identified] (e.g. "User prefers Python over JavaScript", "SOC 2 audit in Q3")
        │
        ├── 1. Insert into PostgreSQL (app.models.Memory)
        │      • id: UUID
        │      • scope: "user" | "workspace"
        │      • content: str
        │
        └── 2. Generate Vector & Upsert to Qdrant (aurenix_memories)
               • vector: 1536d embedding
               • payload: { memory_id, user_id, workspace_id, scope }
```

---

## 3. Scoping & Privacy Controls

* **User-Scoped Memories**: Private to the specific user account across all their workspaces.
* **Workspace-Scoped Memories**: Shared across all verified members of an enterprise workspace (e.g. team conventions, project milestones).
* **Cascading Deletion**: Deleting a memory via `DELETE /api/v1/memories/{id}` atomically deletes the PostgreSQL row and deletes the associated vector from Qdrant.
