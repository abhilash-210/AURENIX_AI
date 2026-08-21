# Aurenix AI — Production Deployment Guide

> **Document Version:** 1.0.0  
> **Status:** Production-Ready Preparation Guide  
> **Target Audience:** DevOps Engineers, Full-Stack AI Engineers, System Administrators

---

## 1. Production Architecture

Aurenix AI is engineered as a containerized multi-tier enterprise AI application. The recommended production architecture balances performance, isolation, maintainability, and cost-effectiveness for single-node VM or cloud container deployments.

```
                             Internet
                                │
                        ┌───────▼───────┐
                        │  Cloudflare   │ (DNS, SSL/TLS, DDoS, Edge Cache)
                        └───────┬───────┘
                                │ HTTPS (443)
                        ┌───────▼───────┐
                        │ Reverse Proxy │ (Nginx / Caddy with Auto-TLS)
                        └──┬─────────┬──┘
             HTTP (3000)   │         │  HTTP (8000)
    ┌──────────────────────┘         └──────────────────────┐
    │                                                       │
┌───▼──────────────────────┐            ┌───────────────────▼──────────────────┐
│ aurenix-ai-frontend      │            │ aurenix-ai-backend                   │
│ (Next.js 16 Standalone)  │            │ (FastAPI + Uvicorn 4 Workers)        │
│ Non-Root (nextjs:1001)   │            │ Non-Root (appuser:appuser)           │
└──────────────────────────┘            └──────────┬───────────────────────────┘
                                                   │ Internal Docker Network
                        ┌──────────────────────────┼───────────────────────────┐
                        │                          │                           │
               ┌────────▼────────┐        ┌────────▼────────┐         ┌────────▼────────┐
               │ PostgreSQL 15   │        │ Qdrant Vector   │         │ Redis 7         │
               │ Relational DB   │        │ Embedding Index │         │ Cache & State   │
               │ [Volume Mount]  │        │ [Volume Mount]  │         │ [Volume Mount]  │
               └─────────────────┘        └─────────────────┘         └─────────────────┘
```

### Architecture Highlights
1. **Frontend**: Next.js 16 compiled in `standalone` output mode running under Node 20 Alpine with non-root security.
2. **Backend**: FastAPI running with Uvicorn multi-process worker pool (`--workers 4`), structured JSON logging, and asynchronous database connections via `asyncpg`.
3. **Database Layer (Internal Only)**: PostgreSQL 15, Qdrant, and Redis operate exclusively on an internal bridge network (`aurenix_internal`), with no exposed host ports to prevent unauthorized internet port scanning.
4. **Vector Store**: Qdrant handles dense vector storage (`text-embedding-3-small`, 1536 dims) with persistent HNSW index volumes.
5. **Reverse Proxy & Edge**: Nginx/Caddy handles SSL termination, gzip/brotli compression, rate limiting, and request buffering for streaming endpoints (SSE).

---

## 2. Prerequisites

### Host System Requirements
* **Operating System**: Ubuntu 22.04 LTS / Debian 12 / RHEL 9 (64-bit x86_64 or ARM64)
* **Hardware**:
  * Minimum: 2 vCPU, 4 GB RAM, 25 GB SSD
  * Recommended: 4 vCPU, 8 GB RAM, 50 GB NVMe SSD
* **Software**:
  * Docker Engine (v24.0+)
  * Docker Compose (v2.20+)
  * Git (v2.30+)
  * OpenSSL (for key generation)

### Third-Party Credentials
* **OpenAI API Key** (Production tier with access to `gpt-4o-mini` and `text-embedding-3-small`)
* **Anthropic API Key** (Optional, for Claude-based agents)
* **Domain Name** pointing to your host server IP via DNS `A` records (e.g., `app.aurenix.ai` and `api.aurenix.ai`).

---

## 3. Environment Variables Reference

| Variable | Dev Default | Production Requirement | Description |
|---|---|---|---|
| `APP_ENV` | `development` | `production` | Enables strict mode & telemetry switches |
| `DEBUG` | `true` | `false` | Disables verbose debug logging & OpenAPI schemas |
| `HOST` | `0.0.0.0` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | `8000` | Server bind port |
| `CORS_ORIGINS` | `http://localhost:3000` | `https://app.yourdomain.com` | Strict whitelist of allowed origins |
| `LOG_LEVEL` | `DEBUG` | `INFO` / `WARNING` | Application log threshold |
| `LOG_FORMAT` | `text` | `json` | Structured JSON output for log aggregators |
| `DATABASE_URL` | SQLite / Local Postgres | `postgresql+asyncpg://...` | Asynchronous PostgreSQL connection DSN |
| `JWT_SECRET_KEY` | Development placeholder | 64-char Hex Key | Strong secret for signing auth tokens (≥32 chars) |
| `JWT_ALGORITHM` | `HS256` | `HS256` | Token signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | `30` | Access token lifespan |
| `OPENAI_API_KEY` | None | `sk-proj-...` | Production OpenAI API Key |
| `QDRANT_URL` | `http://localhost:6333` | `http://qdrant:6333` | Internal vector engine address |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://:pwd@redis:6379/0` | Redis caching & state DSN |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | `https://api.yourdomain.com/api/v1` | Public API endpoint for frontend client |

---

## 4. Step-by-Step Production Deployment

### Step 1: Clone Repository on Server
```bash
git clone https://github.com/abhilash-210/AURENIX_AI.git /opt/aurenix-ai
cd /opt/aurenix-ai
```

### Step 2: Configure Production Secrets
Create and populate the production environment file:
```bash
cp .env.production.example .env.production
chmod 600 .env.production

# Generate secure random keys
openssl rand -hex 32  # Use for JWT_SECRET_KEY
openssl rand -base64 24 # Use for POSTGRES_PASSWORD
openssl rand -base64 24 # Use for REDIS_PASSWORD
```
Edit `.env.production` with `nano` or `vim` and fill in your actual production keys and domain names.

Copy backend environment:
```bash
cp .env.production backend/.env.production
chmod 600 backend/.env.production
```

### Step 3: Run Database Migrations
Before spinning up the web app, ensure the database schema is up to date:
```bash
# Start only the database dependency
docker compose -f docker-compose.prod.yml up -d postgres

# Run Alembic migrations against the live database
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

### Step 4: Build and Launch Services
```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Step 5: Configure Reverse Proxy (Nginx Example)
Create `/etc/nginx/sites-available/aurenix.conf`:
```nginx
server {
    server_name app.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE Streaming support for AI Chat
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```
Enable the site and issue SSL certificates via Certbot:
```bash
sudo ln -s /etc/nginx/sites-available/aurenix.conf /etc/nginx/sites-enabled/
sudo certbot --nginx -d app.yourdomain.com -d api.yourdomain.com
```

---

## 5. Database Migration Procedure

Aurenix AI uses **Alembic** for schema migrations.

### Check Current Migration Status
```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic current
```

### Apply Pending Migrations
```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

### Dry-Run / Generate SQL Script (Offline Mode)
To inspect the SQL before applying to production:
```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head --sql > migration.sql
cat migration.sql
```

### Rollback Last Migration
```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1
```

---

## 6. Health Checks & Monitoring

### Automated Probing
The backend exposes `GET /api/v1/health` which conducts active probes on downstream dependencies:

```bash
curl -f https://api.yourdomain.com/api/v1/health
```

**Expected Healthy Response (`200 OK`):**
```json
{
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "environment": "production",
    "services": {
      "database": {
        "status": "ok",
        "latency_ms": 1.45
      }
    }
  },
  "meta": {
    "request_id": "req-98e3b2"
  }
}
```

### Container Status Verification
```bash
docker compose -f docker-compose.prod.yml ps
```

---

## 7. Persistent Storage & Backup Considerations

### Volume Mapping
Production data is persisted in Docker named volumes:
* `postgres_prod_data` (`/var/lib/postgresql/data`): User accounts, documents metadata, workspaces, chat history, and audit logs.
* `qdrant_prod_data` (`/qdrant/storage`): Dense vector collections and HNSW search indices.
* `redis_prod_data` (`/data`): Append-Only File (AOF) state.

### Automated PostgreSQL Backup Script
Create a daily cron job (`/opt/aurenix-ai/scripts/backup_db.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/aurenix"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

docker exec aurenix_postgres_prod pg_dump -U aurenix -d aurenix_db -F c > "$BACKUP_DIR/aurenix_db_$TIMESTAMP.dump"

# Retain last 14 days of backups
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +14 -delete
```

### Restoring PostgreSQL from Backup
```bash
cat /var/backups/aurenix/aurenix_db_YYYYMMDD.dump | docker exec -i aurenix_postgres_prod pg_restore -U aurenix -d aurenix_db --clean
```

### Qdrant Vector Collection Snapshot
Trigger an automated Qdrant snapshot via REST API:
```bash
curl -X POST "http://localhost:6333/collections/aurenix_documents/snapshots"
```

---

## 8. Secrets Management & Security Posture

1. **Zero Secret Hardcoding**: No API tokens, keys, or passwords exist in source files or Docker images.
2. **File Permissions**: `.env.production` files must always have restricted permissions (`chmod 600`).
3. **Non-Root Containers**: Backend runs as `appuser` (UID 1000) and frontend runs as `nextjs` (UID 1001).
4. **CORS Hardening**: `CORS_ORIGINS` must only list verified production domains; wildcard `*` is strictly forbidden in production.
5. **OpenAPI Protection**: `/docs`, `/redoc`, and `/openapi.json` are automatically disabled when `APP_ENV=production`.
6. **API Key Security**: User API keys for programmatic access are hashed using SHA-256 before database insertion; raw keys are displayed only once.

---

## 9. Rollback Procedures

### Scenario A: Application Code Rollback
If a newly deployed image has bugs:
```bash
# Revert git commit to last stable release tag
git checkout v1.0.0

# Rebuild and restart
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Scenario B: Database Schema Rollback
If a new migration causes query failures:
```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1
docker compose -f docker-compose.prod.yml restart backend
```

---

## 10. Troubleshooting Guide

### 1. Database Connection Timeout (`503 Service Unavailable`)
* **Cause**: PostgreSQL container is still initializing or network misconfiguration.
* **Resolution**:
  ```bash
  docker compose -f docker-compose.prod.yml logs postgres
  docker compose -f docker-compose.prod.yml exec postgres pg_isready -U aurenix
  ```

### 2. SSE Streaming Breaks / Chat Freezes
* **Cause**: Nginx or Cloudflare is buffering responses.
* **Resolution**: Ensure `proxy_buffering off;` and `proxy_set_header Connection '';` are present in your Nginx configuration block for `/api/v1/chat`.

### 3. Out of Memory (OOM) on Vector Search
* **Cause**: Qdrant memory limit reached during bulk document ingestion.
* **Resolution**: Increase host swap or scale server RAM; configure Qdrant `memmap` on disk storage.

---

> [!NOTE]
> This deployment guide is pre-configured and verified for deployment readiness. The application has been fully containerized and tested in local Docker environments. Live production deployment status should only be confirmed after executing these steps on your target production infrastructure.
