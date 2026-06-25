# Resilience Patterns

*Reference guide for the resilience patterns implemented in Resilience Lab.*

---

## Table of Contents

- [Rate Limiting](#rate-limiting)
- [Bulkhead Pattern](#bulkhead-pattern)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Combined Resilience Stack](#combined-resilience-stack)
- [Testing Resilience](#testing-resilience)
- [Monitoring and Metrics](#monitoring-and-metrics)

---

## Rate Limiting

**Pattern**: Sliding window with Redis sorted sets
**Implementation**: FastAPI middleware
**Location**: `services/api/middleware/rate_limit.py`

### Why bother?

Without rate limiting, one misbehaving tenant firing 10,000 req/s can ruin the day for everyone else. Redis as the backend gives us accurate per-window counting without race conditions — the pipeline of `ZREMRANGEBYSCORE + ZCARD + ZADD + EXPIRE` is effectively atomic at the "won't let more than N requests through" level.

### How it works

```python
# All four ops run in a single Redis pipeline (atomic)
ZREMRANGEBYSCORE(key, 0, window_start)   # trim entries older than window
count = ZCARD(key)                        # count what's left
ZADD(key, {uuid: current_time})          # always record this request
EXPIRE(key, window_seconds)

if count >= 60:
    return HTTP 429 Too Many Requests    # request was counted, still rejected
else:
    return Allow
```

**Configuration** (set in `services/api/main.py`):
- Max requests: **60 per 60 seconds** per tenant
- Tenant identification: `X-Tenant` header (defaults to `"default"`)
- Redis key TTL: 60 s — inactive tenants clean themselves up

**Response on limit exceeded**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded for tenant {tenant_id}",
  "limit": "60 requests per 60s",
  "tenant": "{tenant_id}"
}
```
HTTP `429 Too Many Requests`

### Architecture

```
Client Request
     │
     ▼
┌─────────────────────────┐
│ RateLimitMiddleware     │
│                         │
│  1. Extract X-Tenant    │ ← missing header → falls back to "default"
│         │               │
│  2. ZREMRANGEBYSCORE    │ ← trim entries outside window
│  3. ZCARD               │ ← count remaining (before this request)
│  4. ZADD + EXPIRE       │ ← always record, even if we'll deny
│         │               │
│      count >= 60?       │
│       ├── YES → 429     │
│       └── NO  → Allow  │
└─────────────────────────┘
```

### Testing

**Unit tests**: `services/api/tests/test_rate_limit.py`

Covered cases:
- Requests under limit pass through (200 OK)
- Request #61 gets blocked (429)
- Missing `X-Tenant` header → defaults to `"default"` tenant
- Different tenants have separate counters (proper isolation)

Coverage: **>90%**

---

## Bulkhead Pattern

**Pattern**: Resource isolation via connection pool limits
**Implementation**: Envoy circuit breakers
**Location**: `deploy/envoy/envoy-config.yaml`

### Why "bulkhead"?

Named after ship bulkheads — if one compartment floods, the rest of the vessel keeps sailing. Same idea here: if one upstream starts responding slowly and accumulates connections, we don't let it drain the entire proxy pool. Without limits, a single slow pod can stall all traffic through Envoy.

### Configuration (both `api_service` and `payments_service` clusters)

```yaml
circuit_breakers:
  thresholds:
    - priority: DEFAULT
      max_connections: 5         # TCP connection pool to backend pods
      max_pending_requests: 5    # queue depth when no connection is free
      max_requests: 10           # total concurrent HTTP requests
      max_retries: 3             # concurrent retry requests (anti-retry-storm)
```

> **On the numbers**: these are intentionally tight, tuned for a dev/minikube environment
> running 1–2 pods per service. Scale proportionally in production.

### How it works

```
                    Envoy — Bulkhead
┌──────────────────────────────────────────┐
│  Connection Pool     max: 5              │
│  [c1] [c2] [c3] [c4] [c5]              │
│                                          │
│  Request Queue       max: 5              │
│  [r1] [r2] [r3] [r4] [r5]              │
│                                          │
│  Active Requests     max: 10             │
│  [req × 10]                              │
│                                          │
│  Retry Budget        max: 3 concurrent   │
│  [retry] [retry] [retry]                 │
└──────────────────────────────────────────┘
              │
              ▼  When any limit is exceeded:
   HTTP 503 + upstream_rq_pending_overflow++
```

### What each parameter does and why

| Parameter | Value | What it caps | On overflow |
|---|---|---|---|
| `max_connections` | 5 | TCP connections to backend pods | new connections → 503 |
| `max_pending_requests` | 5 | queue when no free connection | immediate 503 |
| `max_requests` | 10 | concurrent HTTP streams total | requests enter the queue |
| `max_retries` | 3 | concurrent retry requests | retry skipped, original error returned |

`max_retries: 3` is the anti-retry-storm guard. Imagine 50 clients each retrying twice after
a 5xx — that's 150 concurrent retries hitting an already struggling upstream. The cap keeps
retries from becoming the cause of the outage they're trying to recover from.

---

## Circuit Breaker Pattern

**Pattern**: Passive health checking via outlier detection
**Implementation**: Envoy outlier detection
**Location**: `deploy/envoy/envoy-config.yaml`

### Bulkhead vs. Circuit Breaker — what's the difference?

A common source of confusion, so let's be explicit:

| Feature | Bulkhead | Circuit Breaker |
|---|---|---|
| **Purpose** | resource isolation | fault isolation |
| **Triggers on** | resource limits exceeded | error rate (5xx responses) |
| **Action** | reject new requests | eject unhealthy host from pool |
| **Response** | HTTP 503 (queue full) | HTTP 503 (host ejected) |
| **Recovery** | immediate (when load drops) | gradual (after ejection time) |
| **Protects** | current service from overload | downstream from a flood of bad requests |

They work together: bulkhead caps connections, circuit breaker removes broken pods from rotation.

### Configuration (both clusters)

```yaml
outlier_detection:
  consecutive_5xx: 3              # eject after 3 consecutive 5xx from a host
  interval: 10s                   # detection scan interval
  base_ejection_time: 30s         # ejection duration (doubles on repeat offenders)
  max_ejection_percent: 50        # at most 50% of hosts ejected at once
  enforcing_consecutive_5xx: 100  # always enforce (100% probability)
  enforcing_success_rate: 100     # also enforce success-rate-based ejection
  success_rate_minimum_hosts: 2   # need at least 2 hosts to compare success rates
  success_rate_request_volume: 10 # need at least 10 req/host to calculate SR
  success_rate_stdev_factor: 1900 # eject if SR < avg − 1.9σ
```

`max_ejection_percent: 50` is the key safety valve. With 2 pods, Envoy will eject at most 1.
Without it: both pods ejected → total outage. Set it too low and a genuinely broken pod stays
in rotation anyway.

### How it works

```
Pods: [Pod-A ✓] [Pod-B ✗] [Pod-C ✓]
               │
    Envoy round-robins traffic
               │
    Pod-B returns 5xx — once, twice, three times
               │
    consecutive_5xx = 3 → EJECT Pod-B for 30s
               │
Active pool:  [Pod-A ✓] [Pod-C ✓]
Ejected:      [Pod-B]   ← probed after 30s; re-added if healthy
```

---

## Combined Resilience Stack

Every request passes through all four defense layers in order:

```
Client Request
     │
     ▼
┌─────────────────────────────────────┐
│ 1. Rate Limiting  (FastAPI)         │  ← 60 req/min/tenant → 429 on excess
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 2. Ingress  (Traefik)               │  ← TLS termination, routes /api/* → Envoy
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 3. Envoy Proxy  (resilience layers) │
│                                     │
│  Bulkhead (circuit_breakers)        │  ← max 5 conn / 5 pending / 10 req
│  Outlier Detection                  │  ← eject after 3× 5xx, max 50% of hosts
│  Retry Policy                       │  ← 2 retries, 200ms per-try timeout
│  Timeout Policy                     │  ← 2s route timeout, 60s idle
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ 4. Backend Services                 │
│    API (FastAPI :8000)              │
│    Payments (FastAPI :8001)         │
└─────────────────────────────────────┘
```

### Failure scenarios covered

| Scenario | Protection | Response |
|---|---|---|
| Traffic spike (>60 req/min/tenant) | Rate Limiting | HTTP 429 |
| Connection pool exhausted | Bulkhead | HTTP 503 |
| Backend pod crashes | Retry Policy | retry on healthy pod (2 attempts) |
| Backend returns 5xx × 3 | Outlier Detection | eject pod for 30s |
| Slow backend (>200ms) | Timeout Policy | per-try abort at 200ms |
| Retry storm | Bulkhead `max_retries: 3` | max 3 concurrent retries |

---

## Testing Resilience

### Fault injection scripts

**Location**: `scripts/fault-inject.sh`

```bash
# Inject 500 errors — exercises outlier detection
./scripts/fault-inject.sh failure

# Inject 2s delay — per-try timeout (200ms) fires, expect 504s
./scripts/fault-inject.sh slow

# Kill a random pod — exercises retry + auto-recovery
./scripts/fault-inject.sh kill

# Clean up all injections
./scripts/fault-inject.sh cleanup
```

### Monitoring during tests

```bash
# Port-forward Envoy admin interface
kubectl port-forward -n resilience-lab svc/envoy-proxy 9901:9901

# Outlier detection — ejection events
curl -s http://localhost:9901/stats | grep outlier_detection

# Bulkhead — how many requests got rejected
curl -s http://localhost:9901/stats | grep rq_pending_overflow

# Retry stats
curl -s http://localhost:9901/stats | grep upstream_rq_retry

# Per-try timeouts (should spike during slow mode)
curl -s http://localhost:9901/stats | grep per_try_timeout
```

### Test rate limiting

```bash
kubectl port-forward -n resilience-lab svc/traefik 8080:80

# Fire 65 requests — 60 should pass, 5 should get 429
# Note: must use a rate-limited path. /api/healthz is rewritten to /healthz
# by Envoy and skipped by the middleware. Use /api/ (→ GET /) instead.
for i in {1..65}; do
    curl -s -o /dev/null -w "%{http_code}\n" \
        -H "X-Tenant: test-tenant" \
        -H "Host: resilience-lab.local" \
        http://localhost:8080/api/
done | sort | uniq -c
# Expected:
# 60 200
#  5 429
```

### Test bulkhead (connection pool exhaustion)

```bash
# 20 concurrent requests will exceed max_connections=5
ab -n 200 -c 20 http://localhost:8080/api/healthz

# Watch overflow counter in real time
watch -n 1 'curl -s http://localhost:9901/stats | grep rq_pending_overflow'
# Expected: rq_pending_overflow > 0 when concurrency > 5
```

---

## Monitoring and Metrics

### Rate Limiting (application-level)

| Metric | Meaning |
|---|---|
| `rl_allowed_total` | requests passed through (labeled by tenant) |
| `rl_denied_total` | requests rejected with 429 (labeled by tenant) |

### Bulkhead (Envoy)

| Metric | Meaning |
|---|---|
| `circuit_breakers.default.cx_active` | active connections (cap: 5) |
| `circuit_breakers.default.rq_pending` | queued requests (cap: 5) |
| `circuit_breakers.default.rq_pending_overflow` | **rejected requests** — the one to alert on |

Alert on `rq_pending_overflow > 0` — it means the bulkhead is actually doing work.

### Circuit Breaker (Envoy)

| Metric | Meaning |
|---|---|
| `outlier_detection.ejections_active` | currently ejected hosts |
| `outlier_detection.ejections_enforced_total` | total ejections since start |
| `outlier_detection.ejections_consecutive_5xx` | ejections triggered by error streaks |

### Retry / Timeout (Envoy)

| Metric | Meaning |
|---|---|
| `upstream_rq_retry` | total retry attempts |
| `upstream_rq_retry_success` | retries that recovered successfully |
| `upstream_rq_retry_overflow` | retries skipped because `max_retries` was hit |
| `upstream_rq_timeout` | request-level timeouts |
| `upstream_rq_per_try_timeout` | per-try timeouts (200ms threshold) |

### Grafana Dashboards

Two dashboards deployed as Helm ConfigMaps:

- **Resilience Dashboard** (`grafana-dashboard-resilience.yaml`) — RPS, error rate, retries, ejections, p95/p99 latency
- **System Overview** (`grafana-dashboard-system-overview.yaml`) — cluster health, pod resource usage

---

## References

**Envoy documentation**:
- [Circuit Breaking](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Retry Semantics](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_routing#retry-semantics)

**Internal docs**:
- [Architecture](ARCHITECTURE.md) — system architecture overview
- [M2 Fault Tests](M2_FAULT_TESTS.md) — raw test data from resilience experiments
- [Deployment](DEPLOYMENT.md) — how to get this running

---

## What changed in this document

The original M3 doc was written mid-milestone (DAY 5/15) and never updated after the implementation
settled. This revision syncs it against the actual code and config. Here's what was wrong and why
it matters:

| # | Severity | What was wrong | What it is now |
|---|---|---|---|
| 1 | High | Rate-limit test used `/api/healthz` — Envoy rewrites it to `/healthz`, which is in `excluded_paths`. The 429s would never appear. | Changed to `/api/` (routes to `GET /`, not excluded) |
| 2 | High | Response JSON showed `detail` + one `error` string. Actual middleware returns `error`, `message`, `limit`, `tenant` (4 fields). | Updated to match `rate_limit.py:68–75` |
| 3 | Medium | Pseudocode used `ZCOUNT`. Actual pipeline: `ZREMRANGEBYSCORE` → `ZCARD` → `ZADD` → `EXPIRE`. Also: `ZADD` runs unconditionally — denied requests are counted too. | Pseudocode and architecture diagram rewritten |
| 4 | Medium | Metric names `rate_limit_allowed_total` / `rate_limit_blocked_total` / `rate_limit_errors_total` don't exist. Actual counters: `rl_allowed_total` / `rl_denied_total` (labeled by tenant). | Table corrected; non-existent error metric removed |
| 5 | Low | For-loop in `bash` block used fish syntax (`for i in (seq…) / end`). | Replaced with `for i in {1..65}; do … done` |

Net diff from original: **−162 lines** (570 → 408), `+237 / −399` in raw diff. Driven by
removing the stale M3 milestone header, schedule table, and "Future" Grafana placeholder.
Content that was wrong is fixed; content that was just outdated is gone.
