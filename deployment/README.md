# deployment/

Container orchestration and infrastructure configuration.

**Planned Sprint:** Sprint 1 (Docker Compose), Sprint 7 (Kubernetes + Helm)

## Structure

```
deployment/
├── docker/
│   ├── docker-compose.yml         # Full local stack (Sprint 1)
│   ├── docker-compose.test.yml    # Isolated test environment
│   └── .env.example               # Environment variable template
├── kubernetes/                    # K8s manifests (Sprint 7)
│   ├── backend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── frontend/
│   ├── postgres/
│   └── redis/
├── helm/                          # Helm chart (Sprint 7)
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
└── README.md
```

## Local Development (Sprint 1+)

```bash
# Start all services
docker compose -f deployment/docker/docker-compose.yml up -d

# View logs
docker compose logs -f backend

# Stop all services
docker compose down
```

## Services (Docker Compose)

| Service | Port | Description |
|---|---|---|
| `backend` | 8000 | FastAPI application |
| `frontend` | 3000 | Next.js application |
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |
| `chromadb` | 8001 | ChromaDB vector store |

> All secrets are loaded from `.env` — copy `.env.example` and fill in your values. Never commit `.env`.
