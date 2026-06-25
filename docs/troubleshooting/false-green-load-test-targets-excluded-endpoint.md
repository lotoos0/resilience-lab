# Load test passes 100% green while testing nothing

**Discovered:** 2026-06-08
**Service:** API (load test tooling)
**Fixed in:** `test(load): switch rate-limit smoke test target to /openapi.json`
(b64a969, preceded by 2b0eb55)

---

## What happened

`tests/load/rate-limit-test-simple.js` is supposed to prove the rate-limit
middleware returns HTTP 429 under sustained load — acceptance criterion for
issue #29. It always ran clean:

```
checks_succeeded...: 100.00% 282 out of 282
✓ status is 200
✓ no rate limit error
rate_limit_429_count...........: 0
```

Beautiful dashboard. Zero signal. The test was green because it politely
walked around the feature it was supposed to validate — a tiny applause
machine for a code path that never ran.

## Symptoms

- Every run, regardless of request rate (50 req/min or 100 req/min),
  produced the same outcome: all 200s, zero 429s.
- No errors, no warnings — textbook false green.
- `rate_limit_429_count` permanently stuck at 0.

## Why it happened

The test sent every request to `GET /healthz`:

```js
const response = http.get(`${BASE_URL}/healthz`, params);
```

But `/healthz` is explicitly in the middleware's exclusion list:

```python
# services/api/middleware/rate_limit.py
excluded_paths: tuple[str, ...] = ("/healthz", "/metrics")

async def dispatch(self, request, call_next):
    if request.url.path in self.excluded_paths:
        return await call_next(request)  # no Redis, no counters, no log line
```

For an excluded path, `dispatch()` returns before touching Redis,
incrementing `rl_allowed_total`/`rl_denied_total`, or emitting a
`rate_limit_check` log line. No matter how much load you throw at
`/healthz`, the middleware never looks at it. A 429 is structurally
impossible.

The original script's own docstring said "Uses /healthz endpoint to avoid
Payments service dependency" — a deliberate choice to dodge one problem that
accidentally created a much bigger one.

## Fix

Pointed the test at `GET /openapi.json` — FastAPI's auto-generated OpenAPI
schema route:

- not in `excluded_paths`, so it goes through the full middleware path
- no dependency on the Payments service (the original reason `/healthz`
  was chosen)
- reliably returns 200

`GET /` was the obvious first candidate, but it currently returns 500 due
to an unrelated `ResponseValidationError` bug (issue #63), so `/openapi.json`
won. Setup still checks `GET /healthz` before the test starts — readiness
checks are still its job.

After the fix, the same test produced real results:

```
rate_limit_429_count...........: 40
successful_requests............: 111
✓ has rate limit error
✓ has tenant in response
```

40 HTTP 429s in the over-limit phase, 111 successful requests in the
under-limit phase. Not "all red" — meaningful signal.

## How I found it

While preparing to verify #29's "load test shows 429 under sustained
pressure" criterion, re-reading `RateLimitMiddleware.dispatch()` made the
early-return for `excluded_paths` obvious. One glance at which endpoint the
k6 script targeted (`/healthz`) immediately explained why it had never
produced a single 429 in any prior run.

## Prevention

- When writing a load test **for** middleware, check its exclusion lists
  first (`excluded_paths`, allowlists, feature flags). Picking an excluded
  target is an easy way to write a test that always passes and never tests
  anything.
- A 100%-green load test is not proof the feature was exercised. Assert on
  the positive signal — make `rate_limit_429_count > 0` a hard threshold,
  not just a soft `check`, so the test fails loudly if the targeted code
  path is never hit.
- Document why a specific endpoint was chosen as the load-test target
  directly in the test file. One comment is enough — it's the first thing
  the next person needs when the target changes or breaks.
