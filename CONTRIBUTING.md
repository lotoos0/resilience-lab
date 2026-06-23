# Contributing to Resilience Lab

This is a solo learning project, but it's structured as if it were a real team repo —
proper CI, code review, runbooks, the works. If you're reading this because you want
to contribute: welcome, and thanks for taking the time.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Reporting Issues](#reporting-issues)
- [Pull Requests](#pull-requests)
- [Commit Format](#commit-format)
- [Branching](#branching)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Development Setup](#development-setup)
- [Milestone Overview](#milestone-overview)
- [Release Flow](#release-flow)

---

## Code of Conduct

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Short version: be respectful,
be constructive, don't be a jerk.

---

## Reporting Issues

Search open issues first — the problem might already be known or in progress.

**Bug reports** should include:
- What you did, what you expected, what actually happened
- Environment (OS, Docker version, Python version, branch)
- Relevant logs (paste them in a code block, not as screenshots)

**Feature requests** should explain the problem being solved, not just the solution.
If it fits a milestone, mention which one.

---

## Pull Requests

### Before you open a PR

1. Branch from `develop`, not `main`
2. Run `make lint` and `make test-unit` — CI will reject failures
3. If it's a non-trivial change, open an issue first so we can discuss scope
4. Update docs if your change affects behavior, deployment, or observability

### PR workflow

```bash
git checkout develop && git pull origin develop
git checkout -b issue-<number>-<short-description>
# ... make changes ...
make lint && make test-unit
git push origin issue-<number>-<short-description>
```

Open the PR against `develop`. Link the issue with `closes #N` in the description.

### Self-merge is fine if

- CI is green (lint + unit + integration + build)
- You tested the change locally
- Docs are updated where relevant
- No breaking changes without a note in the PR body

### PR description

Keep it short and honest. What changed, why, how to verify it. If there's a screenshot
or Grafana graph that shows it working — add it. Evidence from actual runs is always
better than "it should work because the code looks right."

---

## Commit Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/).

```
type(scope): short description

Optional body — use it when the why isn't obvious from the what.

Closes #N
```

**Types:**

| Type | When to use |
|------|-------------|
| `feat` | New functionality |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code change with no behavior change |
| `ci` | CI/CD pipeline changes |
| `chore` | Maintenance (deps, config, cleanup) |
| `security` | CVE patches, security hardening |
| `perf` | Performance improvements |

**Rules:**
- Imperative mood: `add`, not `added` or `adds`
- Lowercase first letter, no period at the end
- Keep the subject under 72 characters
- Scope is optional but useful: `feat(chaos):`, `fix(api):`, `docs(runbooks):`

**Examples:**

```
feat(chaos): add pod kill chaos test and rollback-vs-recover runbook
fix(api): correct return type annotation for GET /
docs(observability): add chaos PromQL queries and finalize M3 DoD
security: bump starlette to 1.3.1 for CVE-2026-48818
```

---

## Branching

Light GitFlow: `develop` is the daily working branch, `main` holds tagged releases only.

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only — tagged, never force-pushed |
| `develop` | Active development, integration target for PRs |
| `issue-<N>-<description>` | Feature or fix branch (preferred naming) |
| `hotfix/<description>` | Urgent fix directly targeting main |

Branch off `develop`, PR back to `develop`. Main gets updated at release time only.

---

## Coding Standards

### Python

PEP 8, enforced by `ruff`. If `make lint` passes, you're good. The main things that
matter in practice:

- Type hints on all function signatures
- Meaningful names — `tenant_id` over `tid`, `payment_response` over `resp`
- No bare `except:` — catch what you expect and let the rest bubble up
- Don't log sensitive data (card numbers, tokens, passwords)

```python
# Good
async def get_payment(payment_id: str) -> dict:
    payment = await repository.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return payment

# Not great — no error handling, no return type
async def get_payment(payment_id):
    return repository.get(payment_id)
```

### Docstrings

Short public functions don't need docstrings if the name and types tell the story.
Longer or tricky functions do — keep them concise, focus on the non-obvious parts.

### Comments

Comments should explain *why*, not *what*. If you need to explain what the code does,
the code probably needs to be clearer.

---

## Testing

### Coverage targets

- Minimum: 80%
- Target: 90%
- Critical paths (auth, payments, rate limiting): 100%

### Test types

**Unit tests** — no external services required, fast feedback:

```bash
make test-unit
```

**Integration tests** — require running services (`make dev` first):

```bash
make dev
make test-integration
```

**All tests with coverage:**

```bash
make dev
make test
pytest --cov=services --cov-report=html
```

### CI requirements

PRs must pass all of these before merge:

1. `make lint` — ruff
2. `make test-unit`
3. `make test-integration`
4. Docker build — images must build cleanly

---

## Development Setup

Prerequisites: Docker 24+, Docker Compose v2+, Python 3.11+, Make.

```bash
git clone https://github.com/lotoos0/resilience-lab.git
cd resilience-lab
make install   # install dev dependencies
make dev       # start all services via Docker Compose
make test      # verify everything works
```

For Kubernetes setup and Helm deployment: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

For project structure and coding conventions: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Milestone Overview

| Milestone | Focus | Status |
|-----------|-------|--------|
| M0 — Bootstrap | Repo, API + Payments, Compose, CI skeleton | Done |
| M1 — Core + CI/CD | Helm, atomic CI/CD, security baseline | Done |
| M2 — Networking & Health | Traefik, Envoy, HPA, PDB, NetworkPolicy | Done |
| M3 — Resilience + Observability | Rate-limit, bulkhead, Prometheus, Grafana, Loki, chaos tests | Done |
| Release | Release notes, CHANGELOG, tag v0.1.0 | In progress |

---

## Release Flow

Releases go through `develop` → `main` → tagged.

```bash
# 1. Make sure develop is clean and all PRs are merged
git checkout develop && git pull

# 2. PR develop → main (via GitHub), then merge

# 3. Tag on main
git checkout main && git pull
git tag -a v0.1.0 -m "Release v0.1.0 — Resilience Lab MVP"
git push origin main --tags

# 4. GitHub Release — attach release notes from RELEASE_NOTES_v0.1.0.md
```

CI builds and publishes versioned Docker images to GHCR on tag push automatically.

---

Questions? Check `docs/`, search [issues](https://github.com/lotoos0/resilience-lab/issues),
or open a new one.
