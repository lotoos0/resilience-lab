# Troubleshooting: Duplicate Prometheus metric registration when running tests together

**Discovered:** 2026-06-07
**Service:** API
**Fixed in:** `test(api): cover main.py to fix codecov/patch failure`

## Problem

Running `services/api/tests/test_main.py` and `services/api/tests/test_rate_limit.py`
together (in either order) crashed with:

```
ValueError: Duplicated timeseries in CollectorRegistry: {'rl_allowed_total', 'rl_allowed', 'rl_allowed_created'}
```

Each file passed fine on its own — only the combination failed.

## Symptoms

- `pytest services/` failed during collection/import, not during a specific test.
- The error pointed at Prometheus `Counter` registration in `rate_limit.py`, even
  though that module is only imported once per file via a relative import.
- Removing a `sys.path.insert(...)` hack from `test_rate_limit.py` (the first suspect)
  did not fix it.

## Root Cause

`services/` had no `__init__.py`, so it was an implicit PEP 420 namespace package.

Pytest's default "prepend" import mode walks up from the test file looking for the
first ancestor *without* `__init__.py` to compute the module's dotted name (rootdir).
That walk stopped at different points depending on which test file pytest imported
first, so the two test files ended up resolving the **same** `rate_limit.py` source
file under **two different module names**:

- `api.middleware.rate_limit` (from one resolution path)
- `services.api.middleware.rate_limit` (from the other)

Python treats these as two separate modules, so `rate_limit.py` was executed twice.
Each execution registers its module-level `Counter("rl_allowed_total", ...)` in the
global `CollectorRegistry` — the second registration raised `ValueError: Duplicated
timeseries`.

A debug `conftest.py` with a `pytest_collectstart` hook printing
`sys.modules` keys made the double-import visible immediately.

## Fix

Add an empty `services/__init__.py`. This turns `services` into a regular package,
so pytest's rootdir walk stops at the same place for every test file, relative
imports resolve to one consistent dotted name (`services.api.middleware.rate_limit`),
and the module loads exactly once.

```bash
touch services/__init__.py
```

Also removed the now-redundant `sys.path.insert(0, str(Path(__file__).parent.parent))`
hack from `test_rate_limit.py` — it was a workaround for the same ambiguity and is
unnecessary once `services` is a proper package.

(An alternative is `--import-mode=importlib` in `pytest.ini`/`pyproject.toml`, which
sidesteps rootdir-based naming entirely — not used here to keep the fix minimal and
avoid a config change that affects every test in the repo.)

## How It Was Found

Adding `services/api/tests/test_main.py` (to fix a Codecov coverage gap, see
[codecov-patch-coverage-untested-module-level-code](./codecov-patch-coverage-untested-module-level-code.md))
imported `main.py`, which imports `rate_limit.py` through
`from services.api.middleware.rate_limit import RateLimitMiddleware`. Combined with
`test_rate_limit.py`'s own relative import of the same module under a different
resolved name, the registry collision surfaced.

## Prevention

- Always put `__init__.py` in every package directory in this repo — don't rely on
  implicit namespace packages, especially when relative imports are used in tests.
- If you see `Duplicated timeseries in CollectorRegistry`, suspect the same module
  being imported under two different dotted names before suspecting the metrics code
  itself.
- A quick check: `python -c "import sys; ...; print([m for m in sys.modules if 'rate_limit' in m])"`
  during collection shows whether a module is loaded more than once.
