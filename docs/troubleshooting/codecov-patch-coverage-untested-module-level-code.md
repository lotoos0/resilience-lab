# Codecov patch check fails — untested module-level code

**Discovered:** 2026-06-07
**Service:** API
**Fixed in:** `test(api): cover main.py to fix codecov/patch failure`

---

## What happened

I added `import logging` and `logging.basicConfig(...)` to
`services/api/main.py` in commit `b53c87d`. Pushed. CI went red:

```
codecov/patch: 0.00% of diff hit (target 81.02%)
```

Zero percent. Not "low coverage" — zero. That's Codecov's way of saying it
doesn't know those lines exist.

## Symptoms

- Red `codecov/patch` check on the commit in GitHub.
- Codecov diff view: `services/api/main.py` at 0.00% patch coverage;
  `services/api/middleware/rate_limit.py` (also changed in the same commit)
  at 100%. Same commit, two files, opposite outcomes.
- Root cause hiding in plain sight: no test in the repo imported
  `services.api.main` at all. Not the new lines — the entire module had 0%
  coverage.

## Why it happened

`main.py` is the FastAPI app entrypoint. Its module-level statements —
`app = FastAPI(...)`, middleware registration, `import logging`,
`logging.basicConfig(...)` — only run when the module is **imported**.

Since no test file ever did `from services.api.main import app` (tests hit
`rate_limit` directly), none of `main.py`'s module-level code was ever
executed in CI. Codecov's patch check looks specifically at *changed* lines
and reports 0% hit because the import that would trigger them never happened.

The new lines didn't introduce the gap — they just made it visible.

## Fix

Added `services/api/tests/test_main.py`:

```python
from fastapi.testclient import TestClient
from ..main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200

def test_metrics_endpoint_available():
    response = client.get("/metrics")
    assert response.status_code == 200
```

The `from ..main import app` line is the actual fix — importing `main`
executes its module-level code, including the new `logging` lines.
Codecov now reports `100.00% of diff hit`.

`/healthz` and `/metrics` were chosen deliberately: both are in
`RateLimitMiddleware`'s `excluded_paths`, so the tests don't need a live
Redis connection. `/` or `/pay` would go through the sliding-window rate
limiter and talk to Redis — not what I want in a unit test that's supposed
to just import a module.

## How I found it

Codecov posted the failing status directly on the commit. The diff view
pinpointed `main.py` at 0% patch coverage. Reproduced locally with:

```bash
pytest services/api/ -q --cov=services.api --cov-report=term-missing
```

`services/api/main.py` went from 0% to ~71% once `test_main.py` existed,
with the 2 changed lines specifically covered.

## Prevention

- Entrypoint modules (`main.py`, `app.py`) need at least a minimal smoke
  test that imports them and hits a Redis-independent endpoint. A module
  that's never imported has 0% coverage on **all** its module-level code —
  including future one-liners near the top.
- Before adding code near the top of a module (imports, `basicConfig`,
  route registration), check whether that module is actually imported by
  any test. `--cov-report=term-missing` shows this in one command.
- Adding a test file that imports a previously-untested module can surface
  other latent bugs — run the full suite together, not just the new file,
  before pushing. (It did here — see
  [pytest-namespace-package-duplicate-prometheus-metrics](./pytest-namespace-package-duplicate-prometheus-metrics.md).)
