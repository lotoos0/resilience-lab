# Troubleshooting: Codecov `patch` check fails on untested module-level code

**Discovered:** 2026-06-07
**Service:** API
**Fixed in:** `test(api): cover main.py to fix codecov/patch failure`

## Problem

After pushing `b53c87d` (added `import logging` and a
`logging.basicConfig(...)` call to `services/api/main.py`), the `codecov/patch`
commit status failed CI:

```
codecov/patch: 0.00% of diff hit (target 81.02%)
```

## Symptoms

- GitHub showed a red `codecov/patch` check on the commit, blocking a clean CI run.
- Codecov's diff view showed `services/api/main.py` at 0.00% HEAD/patch coverage,
  while `services/api/middleware/rate_limit.py` (also touched in the same commit)
  was at 100%.
- No test in the repo imported `services.api.main` at all — `main.py` had 0%
  coverage overall, not just on the new lines.

## Root Cause

`main.py` is the FastAPI app entrypoint. Its top-level statements — including the
two new lines (`import logging`, `logging.basicConfig(...)`) plus `app = FastAPI(...)`,
middleware registration, etc. — only execute when the module is **imported**.

No test file imported `main` (only `rate_limit` was tested directly), so none of
`main.py`'s module-level code, old or new, was ever exercised by the suite. Codecov's
patch check looks specifically at *changed* lines and reports 0% hit because the
import that would trigger them never happened in CI.

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

The `from ..main import app` line is what matters for coverage — importing `main`
executes its module-level code, including the new `import logging` and
`logging.basicConfig(...)` lines, so Codecov now counts them as hit
(`100.00% of diff hit`).

`/healthz` and `/metrics` were chosen deliberately: they're in the rate-limit
middleware's `excluded_paths`, so the tests don't need a live Redis connection
(unlike `/` or `/pay`, which go through `RateLimitMiddleware.dispatch` and talk
to Redis for the sliding-window counters — see `docs/observability.md` for the
metrics/logging this middleware emits).

## How It Was Found

Codecov posted the failing status directly on the commit; the diff view pinpointed
`main.py` at 0% patch coverage. Reproduced locally with:

```bash
pytest services/api/ -q --cov=services.api --cov-report=term-missing
```

which showed `services/api/main.py` going from 0% to ~71% once `test_main.py`
existed, with the changed lines specifically covered.

## Prevention

- Any module that is never imported by a test has 0% coverage on *all* its
  module-level code — including future one-line changes near the top of the file.
  Entrypoint modules (`main.py`, `app.py`, ...) need at least a minimal smoke test
  that imports them and hits a Redis-independent endpoint.
- Before adding code near the top of a module (imports, `basicConfig`, client
  construction, route registration), check whether that module is actually imported
  by any test — `--cov-report=term-missing` shows this at a glance.
- Adding a new test file that imports a previously-untested module can surface
  *other* latent bugs (see
  [pytest-namespace-package-duplicate-prometheus-metrics](./pytest-namespace-package-duplicate-prometheus-metrics.md))
  — run the full suite together, not just the new file, before pushing.
