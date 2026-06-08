# Troubleshooting: Load test passes 100% green while testing nothing

**Discovered:** 2026-06-08
**Service:** API (load test tooling)
**Fixed in:** `test(load): switch rate-limit smoke test target to /openapi.json` (b64a969, preceded by 2b0eb55)

## Problem

`tests/load/rate-limit-test-simple.js` is supposed to prove that the
rate-limit middleware returns HTTP 429 under sustained load (acceptance
criterion for #29). It always ran clean: 100% checks succeeded, every
threshold green, `rate_limit_429_count = 0`.

That looked like "rate limiting works great." It actually meant the test
was structurally incapable of ever producing a 429 — it was validating
nothing about rate limiting at all.

## Symptoms

```
checks_succeeded...: 100.00% 282 out of 282
✓ status is 200
✓ no rate limit error
rate_limit_429_count...........: 0
```

- Every run, regardless of request rate (50/min or 100/min), produced
  exactly the same outcome: all 200s, zero 429s.
- No errors, no warnings — a textbook "false green."

## Root Cause

The test sent every request to `GET /healthz`:

```js
const response = http.get(`${BASE_URL}/healthz`, params);
```

But `/healthz` is explicitly listed in the middleware's exclusion list:

```python
# services/api/middleware/rate_limit.py
excluded_paths: tuple[str, ...] = ("/healthz", "/metrics")

async def dispatch(self, request, call_next):
    if request.url.path in self.excluded_paths:
        return await call_next(request)   # <- returns immediately, no Redis check, no counters, no log line
```

For an excluded path, `dispatch()` returns before touching Redis,
incrementing `rl_allowed_total`/`rl_denied_total`, or emitting a
`rate_limit_check` log line. No matter how much load you throw at
`/healthz`, the middleware never even looks at it — a 429 is structurally
impossible.

(The original script's own docstring said "Uses /healthz endpoint to
avoid Payments service dependency" — a deliberate choice to dodge one
problem that accidentally created a much bigger one.)

## Fix

Pointed the test at `GET /openapi.json` instead — FastAPI's
auto-generated OpenAPI schema route:

- **not** in `excluded_paths`, so it goes through the full middleware path
- has no dependency on the Payments service (the original reason
  `/healthz` was chosen)
- reliably returns 200

(`GET /` was considered first as the "natural" non-excluded, no-Payments
endpoint, but it currently returns 500 due to an unrelated
`ResponseValidationError` bug — see issue #63 — so `/openapi.json` was
used instead.)

After the fix, the same test produced real, meaningful results:

```
rate_limit_429_count...........: 40
successful_requests............: 111
✓ has rate limit error
✓ has tenant in response
```

## How It Was Found

While preparing to verify #29's "load test shows 429 under sustained
pressure" criterion, re-reading `RateLimitMiddleware.dispatch()` made the
early-return for `excluded_paths` obvious — and a quick check of which
endpoint the existing k6 script targeted (`/healthz`) immediately
explained why it had never produced a single 429 in any prior run.

## Prevention

- When writing a load/smoke test **for** a piece of middleware, check its
  exclusion/bypass lists first (`excluded_paths`, allowlists, feature
  flags) — picking an excluded target is an easy way to write a test that
  always passes and never tests anything.
- A 100%-green load test result is not proof the feature was exercised.
  Assert on the *positive* signal you're trying to prove exists — e.g.
  make `rate_limit_429_count > 0` a hard threshold (not just a soft
  `check`), so the test fails loudly if the targeted code path is never
  hit, regardless of why.
- Document *why* a specific endpoint was chosen as the load-test target
  directly in the test file (a one-line comment is enough) — it's the
  first thing the next person needs when the target endpoint changes or
  breaks.

## Additional Resources

- `services/api/middleware/rate_limit.py` — `excluded_paths` and `dispatch()`
- [stale-deployed-image-breaks-observability.md](stale-deployed-image-breaks-observability.md) — found in the same verification pass
- Issue #29 — the verification work that surfaced this
- Issue #63 — the `GET /` bug that ruled out the obvious alternative target
