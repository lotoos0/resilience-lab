# Duplicate Prometheus metrics when running tests together

**Discovered:** 2026-06-07
**Service:** API
**Fixed in:** `test(api): cover main.py to fix codecov/patch failure`

---

## What happened

Running `test_main.py` and `test_rate_limit.py` together crashed immediately:

```
ValueError: Duplicated timeseries in CollectorRegistry:
{'rl_allowed_total', 'rl_allowed', 'rl_allowed_created'}
```

Each file passed fine on its own. The combination blew up during collection,
before a single test ran. Bonus: it surfaced as a Prometheus error, not a
pytest import error, which sent me looking in completely the wrong place
first.

## Symptoms

- `pytest services/` failed during collection, not during a specific test.
- The error pointed at `Counter` registration in `rate_limit.py`, even
  though that module was imported once per file via a relative import.
- Removing a `sys.path.insert(...)` hack from `test_rate_limit.py` (first
  suspect) did nothing.

## Why it happened

`services/` had no `__init__.py`, making it an implicit PEP 420 namespace
package.

Pytest's default "prepend" import mode walks up from each test file looking
for the first ancestor *without* `__init__.py` to compute the module's
dotted name. That walk stopped at different points depending on which test
file pytest imported first. The same `rate_limit.py` source file ended up
registered under two different module names:

- `api.middleware.rate_limit` (one resolution path)
- `services.api.middleware.rate_limit` (the other)

Python treats these as two separate modules, so `rate_limit.py` was executed
twice. Each execution registered its module-level
`Counter("rl_allowed_total", ...)` in the global `CollectorRegistry` — the
second registration raised `ValueError: Duplicated timeseries`.

A debug `conftest.py` with a `pytest_collectstart` hook printing
`sys.modules` keys made the double-import visible immediately.

## Fix

One file:

```bash
touch services/__init__.py
```

Turning `services/` into a regular package forces pytest's rootdir walk to
stop at the same place for every test file. Relative imports now resolve to
one consistent dotted name (`services.api.middleware.rate_limit`) and the
module loads exactly once.

Also removed the now-redundant `sys.path.insert(0, ...)` hack from
`test_rate_limit.py` — it was a workaround for the same ambiguity and
became unnecessary once `services` was a proper package.

(Alternative: `--import-mode=importlib` in `pytest.ini` sidesteps
rootdir-based naming entirely — not used here to keep the fix minimal and
avoid a config change that affects every test in the repo.)

## How I found it

Adding `test_main.py` to fix a Codecov coverage gap (see
[codecov-patch-coverage-untested-module-level-code](./codecov-patch-coverage-untested-module-level-code.md))
imported `main.py`, which imports `rate_limit.py` via
`from services.api.middleware.rate_limit import RateLimitMiddleware`.
Combined with `test_rate_limit.py`'s own relative import resolving the same
module under a different name, the registry collision surfaced. One fix
unlocked another bug — classic.

## Prevention

- Put `__init__.py` in every package directory — don't rely on implicit
  namespace packages when relative imports are in play.
- If you see `Duplicated timeseries in CollectorRegistry`, suspect the same
  module imported under two different dotted names before suspecting the
  metrics code itself.
- Quick diagnostic: `python -c "import sys; print([m for m in sys.modules if 'rate_limit' in m])"` during collection shows whether a module is loaded more than once.
