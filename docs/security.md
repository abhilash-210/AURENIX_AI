# Aurenix AI — Enterprise Security & Compliance Architecture

> **Scope:** Authentication, Authorization (RBAC), Secret Sanitization, Rate Limiting, Audit Logging  
> **Status:** Hardened & Tested

---

## 1. Security Architecture Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AURENIX AI SECURITY DEFENSE-IN-DEPTH                     │
├───────────────────────┬─────────────────────────────────────────────────────────┤
│ Security Layer        │ Implementation Mechanism                                │
├───────────────────────┼─────────────────────────────────────────────────────────┤
│ Transport Security    │ TLS 1.3 Termination, Strict CORS Origins                │
│ Authentication        │ JWT Bearer Tokens (HS256) + Enterprise SHA-256 API Keys │
│ Authorization (RBAC)  │ Role hierarchy: Owner > Admin > Member > Viewer         │
│ Secret Sanitization   │ Automatic log masking for OpenAI, Anthropic, JWT, Keys  │
│ Rate Limiting         │ Sliding-window token bucket (120 req/min, 429 Retry)    │
│ Multi-Tenant Isolation│ Workspace-level scoping in PostgreSQL and Qdrant vectors│
│ Audit Logging         │ Immutable audit trail in PostgreSQL for compliance      │
└───────────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 2. Role-Based Access Control (RBAC)

| Workspace Role | Read Documents | Upload Documents | Delete Documents | Invite Members | Manage API Keys |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Owner** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Admin** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Member** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Viewer** | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 3. Secret Sanitization in Logs

All log formatters pass messages and metadata dictionaries through regex sanitizers that redact high-entropy keys (`sk-proj-...`, `sk-ant-...`, `Bearer ...`, `ey...`) before writing to stdout or disk.
