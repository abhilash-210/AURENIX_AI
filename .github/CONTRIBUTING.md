# Contributing to Aurenix AI

Thank you for your interest in contributing! This guide explains how to work with the repository effectively.

---

## Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, sprint-complete code only |
| `develop` | Integration branch for active sprint work |
| `sprint-N/feature-name` | Feature branches off `develop` |

**Create a branch:**
```bash
git checkout develop
git checkout -b sprint-1/jwt-auth
```

---

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

**Types:**

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change with no feature/fix |
| `test` | Adding or updating tests |
| `chore` | Build scripts, CI, dependencies |
| `perf` | Performance improvement |

**Examples:**
```
feat(rag): add recursive text chunking pipeline
fix(auth): handle expired refresh token gracefully
docs(api): add retrieval endpoint schema
test(agents): add supervisor routing unit tests
```

---

## Pull Request Process

1. Ensure your branch is up to date with `develop`.
2. Run the full test suite: `pytest tests/`.
3. Ensure linting passes: `ruff check . && mypy .`.
4. Fill in the PR template completely.
5. Request at least one reviewer.
6. Merge only after CI passes and review is approved.

---

## Code Standards

- **No secrets in code.** All configuration via environment variables.
- **No placeholder implementations.** Every merged function must work.
- **Type hints everywhere** in Python. Use `mypy --strict` as a guide.
- **Docstrings on all public functions and classes.**
- **Test coverage > 70%** for new modules.

---

## Development Setup

Full setup instructions will be added in Sprint 1 when `backend/` is initialised.

For now:

```bash
git clone https://github.com/your-org/aurenix-ai.git
cd aurenix-ai
# Review docs/ to understand the architecture before writing any code
```
