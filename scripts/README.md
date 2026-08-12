# scripts/

Developer utility scripts for setup, seeding, linting, and maintenance.

## Available Scripts

> Scripts will be added progressively each sprint. All scripts are idempotent and safe to re-run.

| Script | Sprint | Description |
|---|---|---|
| `setup.sh` | Sprint 1 | Bootstrap local development environment |
| `seed_db.py` | Sprint 1 | Populate database with development test data |
| `ingest_sample_docs.py` | Sprint 2 | Ingest sample documents into vector store |
| `run_evaluation.py` | Sprint 6 | Run RAGAS evaluation on a saved conversation set |
| `check_secrets.sh` | Sprint 0 | Scan for accidentally committed secrets |

## Usage

```bash
# Check for accidentally committed secrets (run before every commit)
bash scripts/check_secrets.sh

# Bootstrap local dev (Sprint 1+)
bash scripts/setup.sh

# Seed development database (Sprint 1+)
python scripts/seed_db.py
```

## Script Standards

- Every script must be idempotent (safe to run multiple times)
- Every script must print what it is doing to stdout
- No script may require manual interactive input
- Secrets are read from environment variables, never script arguments
