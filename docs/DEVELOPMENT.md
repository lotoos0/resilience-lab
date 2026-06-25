# 💻 Development Guide

**Resilience Lab — Developer Documentation**

*Last updated: June 25, 2026*

---

> **Author's note:** This guide covers local development from zero to running tests.
> The project has two FastAPI services, four infrastructure containers, a full
> Kubernetes/Helm deployment path, and chaos-engineering scripts. If you just
> want to run tests quickly — jump straight to [Getting Started](#getting-started).

> **What this guide adds (vs. the November 2025 version):**
> The original doc had 8 sections, 3 development paths, and 0 mentions of Kubernetes.
> This version has **12 sections** and covers **3 dev paths** (venv / full deps / Docker-only),
> **24 documented `make` targets**, a full **Kubernetes & Helm** section that was
> completely missing, **k6 load tests** in `tests/load/`, a corrected branch strategy
> (`develop` → `main` flow, not flat), and removed two stale placeholders
> (`test_payments.py (future)` and the stale M1 Alembic migration block).
> Written because the project grew from a two-service Docker Compose demo into a
> full resilience platform with Envoy, Traefik, Prometheus, and Loki — and the doc hadn't kept up.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guide](#testing-guide)
- [Kubernetes & Helm](#kubernetes--helm)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Getting Help](#getting-help)
- [Next Steps](#next-steps)

---

## Getting Started

### Prerequisites

```bash
# Required
docker --version        # Docker 24+
docker compose version  # v2+ (the space matters — old "docker-compose" works too)
python --version        # Python 3.11+
make --version          # GNU Make

# Required for Kubernetes path
kubectl version         # 1.28+
helm version            # 3.12+
minikube version        # 1.32+ (or any local k8s cluster)

# Nice to have
k9s version             # Kubernetes TUI — genuinely makes your life easier
git --version           # Git 2.40+
```

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lotoos0/resilience-lab.git && cd resilience-lab
   ```

2. **Install development dependencies** (lightweight — no PostgreSQL headers needed):
   ```bash
   make install
   ```

3. **Start services** (Docker Compose path):
   ```bash
   make dev
   ```

4. **Verify setup**:
   ```bash
   make ps && make test
   ```

That's 4 steps. If step 3 fails, check that Docker daemon is actually running (yes, that happens).

---

## Development Environment

### Option 1: Virtual Environment (Recommended for fast iteration)

```bash
make install            # Creates venv + installs requirements-dev.txt (~10 packages)
source venv/bin/activate
make dev                # Starts 4 Docker containers: api, payments, postgres, redis
```

**Why this approach:** Test execution is ~5x faster than the Docker-only path because
pytest runs natively. IDE type checking, linting, and autocomplete also work out of the box.

**Limitation:** Requires local Python 3.11+. The dev dependencies (`requirements-dev.txt`)
are intentionally kept lightweight — no PostgreSQL headers, no Redis C libs.

### Option 2: Full Dependencies (for integration testing locally)

```bash
make install-full       # Installs requirements.txt — needs postgresql-libs on the system
make dev
make test-all
```

Use this when you need to run integration tests against real Postgres/Redis locally
(outside Docker). Normally you won't need it — `make test` skips integration tests.

### Option 3: Docker-Only (no local Python)

```bash
make dev
make test-docker        # Spins up python:3.11-slim, installs deps, runs pytest
```

Slower (rebuilds the env each time), but works on any machine with Docker.
Good for CI-parity checks.

### Recommended Tools

**Editor**
- Any editor with LSP support. I use Neovim; VS Code with the Python extension also works well.
  - For VS Code: Python + Docker + YAML extensions

**Kubernetes**
- `k9s` — curses TUI for Kubernetes, makes pod logs/exec/delete actually pleasant
- `kubectl` — mandatory
- `helm` — mandatory for the deployment path

**Database**
- `pgAdmin` or `DBeaver` for PostgreSQL
- `Redis Insight` for Redis

**API Testing**
- FastAPI's built-in Swagger UI at `http://localhost:8000/docs` and `http://localhost:8001/docs`
- `httpx` (already in dev deps) or HTTPie for scripted requests

---

## Development Workflow

### Daily Workflow

```bash
# 1. Start fresh
git pull origin develop
make dev

# 2. Feature branch off develop
git checkout -b feature/your-feature

# 3. Dev loop
# Edit code...
make test               # Fast — unit tests only, ~seconds
make lint               # ruff check (fast, strict)

# 4. Before pushing
make test               # All unit tests pass?
make lint               # Zero warnings

# 5. Ship it
git add <specific-files>
git commit -m "feat: your feature description"
git push origin feature/your-feature
# → open PR targeting develop, not main
```

### Branch Strategy

```
main     (production — tagged releases only)
  └── develop  (integration — where feature branches are merged)
        ├── feature/feature-name
        ├── fix/bug-description
        ├── chore/maintenance-task
        └── docs/what-changed
```

Feature branches target `develop`. `develop` is merged into `main` at release time.
PRs require at least one passing CI run before merge.

**Branch naming**:
| Prefix | When to use |
|--------|-------------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `chore/` | Maintenance, deps, refactoring |
| `docs/` | Documentation-only changes |
| `test/` | Experiments or test-only changes |

---

## Coding Standards

### Python Style

PEP 8, enforced by `ruff`. Chose ruff because it's 10–100x faster than flake8
and covers formatting on top of linting — one tool instead of three.

```python
# Good
def process_payment(amount: float, currency: str) -> dict:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    ...

# Bad
def ProcessPayment(amt, curr):
    if amt<=0: raise ValueError("bad amount")
    ...
```

### Type Hints

Always. Python is dynamically typed, which is great until it isn't.

```python
# Good ✅
from typing import Any

def get_payments(tenant_id: str, limit: int = 10) -> list[dict[str, Any]]:
    ...

# Bad ❌
def get_payments(tenant_id, limit=10):
    ...
```

Note: prefer built-in `list[...]`, `dict[...]` over `typing.List`, `typing.Dict`
(Python 3.9+ syntax, works fine here since we target 3.11+).

### Pydantic Models

Use Pydantic v2 for all data validation at service boundaries:

```python
from pydantic import BaseModel, Field

class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, description="Must be > 0")
    currency: str = Field(pattern="^[A-Z]{3}$")
    tenant_id: str = "default"

    model_config = {
        "json_schema_extra": {
            "example": {"amount": 100.0, "currency": "USD"}
        }
    }
```

Note: the old `class Config:` syntax is Pydantic v1 — use `model_config` dict.

### Error Handling

```python
from fastapi import HTTPException, status

# Good ✅ — explicit status codes, meaningful messages
async def get_payment(payment_id: str):
    payment = await repository.get(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found"
        )
    return payment

# Bad ❌ — let the caller discover the failure themselves
async def get_payment(payment_id: str):
    return repository.get(payment_id)
```

### Logging

Use structured logging with `extra={}` so logs are parseable by Loki:

```python
import logging

logger = logging.getLogger(__name__)

logger.info(
    "Payment processed",
    extra={"payment_id": payment_id, "amount": amount, "currency": currency}
)

# Never log sensitive data
logger.info(f"Processing payment for user {user_id}")   # OK
logger.info(f"Credit card: {card_number}")              # ❌ NEVER
```

---

## Testing Guide

### Test Structure

```
tests/
├── test_sanity.py       # Basic smoke checks — imports, health endpoints
├── test_integration.py  # End-to-end flows (@pytest.mark.integration)
└── load/
    ├── rate-limit-test.js         # k6 load test — full rate-limit scenario
    └── rate-limit-test-simple.js  # k6 load test — simplified version
```

Coverage target: **80% minimum**, 90% in practice. Below 80% is just carelessness —
above 90% on a project this size is usually over-engineered mocking.

### Test Commands

```bash
make test               # Unit tests only (no services needed) — default, use this most
make test-unit          # Same as above
make test-all           # All tests including integration (requires: make dev first)
make test-integration   # Integration tests only (requires: make dev first)
make test-docker        # Run pytest inside a Docker container (no local Python needed)

# Manual options
pytest --cov=services --cov-report=html   # Coverage report → htmlcov/index.html
pytest tests/test_sanity.py -v            # Specific file
pytest -k "test_payment" -v               # By name pattern
```

### Writing Unit Tests

```python
# tests/test_payments.py
import pytest
from services.payments.main import PaymentProcessRequest

def test_payment_request_validation():
    req = PaymentProcessRequest(amount=100, currency="USD")
    assert req.amount == 100

    with pytest.raises(ValueError):
        PaymentProcessRequest(amount=-50, currency="USD")
```

### Writing Integration Tests

Mark them explicitly — CI skips them unless services are confirmed up:

```python
import pytest, requests

pytestmark = pytest.mark.integration

def test_payment_flow():
    response = requests.post(
        "http://localhost:8001/process",
        json={"amount": 100, "currency": "USD"}
    )
    assert response.status_code == 201
    payment_id = response.json()["payment_id"]

    response = requests.get(f"http://localhost:8001/payments/{payment_id}")
    assert response.status_code == 200
```

### Load Tests (k6)

Load tests live in `tests/load/` and target the rate-limiter (Redis-backed, 10 req/min
per tenant by default). Requires k6 installed locally:

```bash
k6 run tests/load/rate-limit-test-simple.js   # Quick sanity check
k6 run tests/load/rate-limit-test.js          # Full scenario with stages
```

---

## Kubernetes & Helm

The full production deployment path uses Kubernetes (Minikube for local dev)
with Helm. The chart lives in `deploy/helm/`.

### Local Kubernetes Setup

```bash
minikube start --driver=docker   # or whatever driver you prefer
```

### Helm Commands

```bash
make helm-deps      # Build Helm chart dependencies (subcharts)
make helm-lint      # Lint the chart — do this before helm-up-dev

make helm-up-dev    # Install/upgrade into resilience-lab namespace (values-dev.yaml)
make helm-test      # Run Helm test hooks (smoke tests inside the cluster)
make helm-down      # Uninstall the release

make rollback-1     # Roll back to revision 1 (replace 1 with target revision)
```

### Stack Overview

After `make helm-up-dev`, the cluster has:

| Component | Purpose |
|-----------|---------|
| `api` | FastAPI gateway, port 8000 |
| `payments` | FastAPI payments service, port 8001 |
| `postgres` | Primary data store |
| `redis` | Rate-limiter backend |
| `envoy` | Front-proxy with retry/timeout/circuit-breaker policies |
| `traefik` | Ingress controller |
| `prometheus` | Metrics scraping |
| `loki` | Log aggregation |

The `deploy/` directory structure:

```
deploy/
├── helm/           # Main Helm chart
├── envoy/          # Envoy front-proxy config
├── traefik/        # Traefik ingress config
├── prometheus/     # Prometheus scrape rules + alerts
└── loki/           # Loki + Promtail config
```

### Building Images for Minikube

Images must be built inside Minikube's Docker daemon:

```bash
eval (minikube docker-env)      # fish shell
# or: eval $(minikube docker-env) for bash/zsh

docker build -t api:local -f services/api/Dockerfile .
docker build -t payments:local -f services/payments/Dockerfile .
```

Then deploy with `pullPolicy: IfNotPresent` + `tag: local` in `values-dev.yaml`.
If you forget `eval (minikube docker-env)`, the cluster will try to pull from Docker Hub
and fail with `ImagePullBackOff`. Classic.

---

## Debugging

### Local Debugging

#### FastAPI Debug Mode

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True, log_level="debug")
```

#### VS Code Debugger

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Payments Service",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/services/payments/main.py",
            "console": "integratedTerminal",
            "env": {
                "DATABASE_URL": "postgresql://resilience:resilience@localhost:5432/resilience_db",
                "REDIS_URL": "redis://localhost:6379"
            }
        }
    ]
}
```

### Container Debugging

```bash
make logs               # All services
make logs-api           # api only
make logs-payments      # payments only

docker compose logs -f payments          # Follow real-time
docker compose exec payments bash        # Shell into container
docker compose exec payments env         # Check env vars
docker compose exec payments curl http://localhost:8001/healthz   # Connectivity check
```

### Database Debugging

```bash
# PostgreSQL
docker compose exec postgres psql -U resilience -d resilience_db
# \dt           → list tables
# \d payments   → describe table
# SELECT * FROM payments;

# Redis
docker compose exec redis redis-cli
# KEYS *
# TTL <key>
# GET <key>
```

### Chaos / Fault Injection

```bash
scripts/fault-inject.sh failure  # Inject 50% failure rate into payments service
scripts/fault-inject.sh slow     # Inject latency (default: 3s delay)
scripts/fault-inject.sh kill     # Kill a random payments pod (k8s path only)
```

See `docs/runbooks/` for scenario-specific runbooks.

---

## Common Tasks

### Adding a New Endpoint

1. **Define Pydantic model**:
   ```python
   class PaymentStatusRequest(BaseModel):
       payment_id: str
   ```

2. **Add route**:
   ```python
   @app.get("/payments/{payment_id}/status")
   async def get_payment_status(payment_id: str):
       ...
   ```

3. **Add tests** — unit first, integration if it hits DB/Redis

4. **Docs are automatic** via FastAPI's OpenAPI generation

### Adding a New Service

1. Create service directory with the standard layout:
   ```
   services/new-service/
   ├── Dockerfile
   ├── main.py
   └── __init__.py
   ```

2. Add to `docker-compose.yml`

3. Add Helm subchart under `deploy/helm/charts/`

4. Add to CI/CD pipeline (`.github/workflows/`)

5. Write tests and update README

---

## Troubleshooting

### Port Already in Use

```bash
lsof -i :8000          # Find what's squatting on the port
kill -9 <PID>          # Evict it
```

### Docker Issues

```bash
make clean             # Down + prune (safe)
make build && make dev # Rebuild and restart

# Nuclear option — removes ALL Docker data on the machine, not just this project
docker system prune -a --volumes
```

### Tests Failing

```bash
make ps                                # Are all 4 containers actually running?
curl http://localhost:8000/healthz     # API up?
curl http://localhost:8001/healthz     # Payments up?
make logs                              # What are they complaining about?

# Reset
make down && make clean && make dev
```

### Import Errors

```bash
make clean-venv && make install        # Nuke and rebuild venv
```

### Helm / Kubernetes Issues

```bash
kubectl get pods -n resilience-lab            # Pod status
kubectl describe pod <name> -n resilience-lab # Detailed events (useful for ImagePullBackOff)
kubectl logs <pod> -n resilience-lab          # Pod logs
helm list -n resilience-lab                   # Release status
```

---

## Best Practices

### Configuration Management

Use environment variables, never hardcode:

```python
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://resilience:resilience@localhost:5432/resilience_db"
)
```

### Async I/O

Use `async/await` for all network I/O:

```python
async def get_payment(payment_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/payments/{payment_id}")
        return response.json()
```

### Security

```python
logger.info(f"Processing payment for user {user_id}")  # OK
logger.info(f"Credit card: {card_number}")             # ❌ NEVER — logs are indexed
```

- Validate all external inputs with Pydantic models
- Use `status.*` constants instead of raw HTTP codes (self-documenting)
- Never commit `.env` files with real credentials

---

## Getting Help

- **Docs**: `docs/` directory — start with `ARCHITECTURE.md`
- **Issues**: [GitHub Issues](https://github.com/lotoos0/resilience-lab/issues)
- **API Docs**: `http://localhost:8000/docs` and `http://localhost:8001/docs` (when running)

---

## Next Steps

1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) — system design and component relationships
2. Read [DEPLOYMENT.md](./DEPLOYMENT.md) — full Kubernetes deployment walkthrough
3. Read [observability.md](./observability.md) — Prometheus + Grafana + Loki setup
4. Contribute — see [CONTRIBUTING.md](../CONTRIBUTING.md)
