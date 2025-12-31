# M3 Resilience Patterns

**Resilience Lab - M3 Milestone Documentation**

*Last updated: December 05, 2025*

---

## Overview

This document describes the resilience patterns implemented in Milestone M3 (Resilience + Observability). These patterns protect services from cascading failures, resource exhaustion, and traffic spikes.

**M3 Scope (Dec 1-15, 2025):**
- Rate Limiting (Redis-based per-tenant throttling)
- Bulkhead Isolation (Envoy circuit breakers)
- Canary Deployments (progressive traffic shifting)
- Observability (Prometheus, Grafana, Loki)

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

**Pattern**: Token bucket with sliding window algorithm
**Implementation**: FastAPI middleware with Redis backend
**Status**: ✅ **COMPLETE** (DAY19-DAY21)

### What is Rate Limiting?

Rate limiting controls the number of requests a client can make within a time window. This prevents:
- API abuse and DoS attacks
- Resource exhaustion from traffic spikes
- Unfair resource consumption by single tenants

### Implementation Details

**Location**: `services/api/middleware/rate_limit.py`

**Algorithm**: Sliding window with Redis sorted sets
```python
# Pseudo-code
window_start = current_time - 60s
count = ZCOUNT(key, window_start, current_time)
if count >= 60:
    return HTTP 429 Too Many Requests
else:
    ZADD(key, current_time, unique_id)
    return Allow request
```

**Configuration**:
- **Max requests**: 60 per minute per tenant
- **Window**: 60 seconds (sliding)
- **Storage**: Redis sorted sets with TTL
- **Tenant identification**: `X-Tenant` header (default: "default")

**Response on limit exceeded**:
```json
{
  "detail": "rate_limit_exceeded",
  "error": "Too many requests. Limit: 60 requests per 60 seconds."
}
```
HTTP Status: `429 Too Many Requests`

### Architecture

```
Client Request
     │
     ▼
┌─────────────────────────┐
│ RateLimitMiddleware     │
│ ┌─────────────────────┐ │
│ │ 1. Extract Tenant   │ │ ← X-Tenant header
│ └──────────┬──────────┘ │
│            │             │
│ ┌──────────▼──────────┐ │
│ │ 2. Check Redis      │ │ ← ZCOUNT sorted set
│ │    Count requests   │ │
│ └──────────┬──────────┘ │
│            │             │
│       ┌────┴────┐        │
│       │ > 60?   │        │
│       └────┬────┘        │
│            │             │
│      ┌─────┴─────┐       │
│      │           │       │
│    YES          NO       │
│      │           │       │
│   ┌──▼──┐    ┌───▼───┐  │
│   │ 429 │    │ ZADD  │  │ ← Add to sorted set
│   └─────┘    │ Allow │  │
│              └───────┘  │
└─────────────────────────┘
```

### Testing

**Unit tests**: `services/api/tests/test_rate_limit.py`

Test cases:
- ✅ Requests under limit are allowed (200 OK)
- ✅ Requests over limit are blocked (429)
- ✅ Missing X-Tenant header uses "default" tenant
- ✅ Different tenants have separate limits

**Coverage**: 90%+

### Kubernetes Deployment

**Helm values** (`deploy/helm/charts/api/values.yaml`):
```yaml
env:
  - name: REDIS_HOST
    value: "redis"
  - name: REDIS_PORT
    value: "6379"
```

**Required**: Redis must be deployed in the same namespace.

---

## Bulkhead Pattern

**Pattern**: Resource isolation and connection pooling
**Implementation**: Envoy circuit breakers
**Status**: ✅ **COMPLETE** (DAY21)

### What is Bulkhead?

Bulkhead pattern isolates resources to prevent cascading failures. Named after ship bulkheads that prevent one flooded compartment from sinking the entire vessel.

**Prevents**:
- Connection pool exhaustion
- Thread pool starvation
- Memory exhaustion from unlimited queuing
- Cascading failures across services

### Implementation Details

**Location**: `deploy/envoy/envoy-config.yaml`

**Configuration for each cluster** (`api_service`, `payments_service`):
```yaml
circuit_breakers:
  thresholds:
    - priority: DEFAULT
      max_connections: 100         # TCP connection pool
      max_pending_requests: 50     # Request queue limit
      max_requests: 100            # Concurrent HTTP/2 requests
      max_retries: 3               # Concurrent retry limit
```

### How It Works

```
                    Envoy Circuit Breaker
┌──────────────────────────────────────────────────┐
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Connection Pool (max: 100)            │     │
│  │  ┌───┐ ┌───┐ ┌───┐       ┌───┐        │     │
│  │  │ 1 │ │ 2 │ │ 3 │  ...  │100│        │     │
│  │  └───┘ └───┘ └───┘       └───┘        │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Request Queue (max: 50)               │     │
│  │  [Req] [Req] [Req] ... [Req]          │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Active Requests (max: 100)            │     │
│  │  [HTTP/2 Stream 1] [Stream 2] ...      │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Retry Budget (max: 3 concurrent)      │     │
│  │  [Retry 1] [Retry 2] [Retry 3]         │     │
│  └────────────────────────────────────────┘     │
│                                                  │
└──────────────────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────┐
        │  When limit exceeded:   │
        │  → HTTP 503 Unavailable │
        │  → upstream_rq_pending_ │
        │    overflow (stat)      │
        └─────────────────────────┘
```

### Resource Limits Explained

#### 1. max_connections (100)
- **What**: Maximum TCP connections to backend service
- **Why**: Prevents connection exhaustion on backend pods
- **Overflow**: New connections return `503 Service Unavailable`

#### 2. max_pending_requests (50)
- **What**: Maximum requests waiting in queue for available connection
- **Why**: Prevents unbounded memory growth from queueing
- **Overflow**: New requests immediately rejected with `503`

#### 3. max_requests (100)
- **What**: Maximum concurrent HTTP/2 requests (across all connections)
- **Why**: Limits total load on backend regardless of connection count
- **Overflow**: Requests queue up (until max_pending_requests hit)

#### 4. max_retries (3)
- **What**: Maximum concurrent retry requests across all clients
- **Why**: Prevents retry storms during outages
- **Overflow**: Retries skipped, original error returned

### Benefits

**Resource Isolation**:
- API service failure doesn't affect Payments service
- One tenant's traffic spike can't exhaust all connections

**Graceful Degradation**:
- `503` error is better than cascading timeouts
- Fast failure (immediate rejection vs. queue timeout)

**Predictable Performance**:
- Bounded resource usage
- No "mystery" slowdowns from queue buildup

### Monitoring

**Envoy Admin Interface** (port 9901):
```bash
# View circuit breaker stats
curl http://localhost:9901/stats | grep circuit_breaker

# Example output:
cluster.api_service.circuit_breakers.default.cx_active: 42
cluster.api_service.circuit_breakers.default.cx_open: 100
cluster.api_service.circuit_breakers.default.rq_active: 87
cluster.api_service.circuit_breakers.default.rq_pending: 12
cluster.api_service.circuit_breakers.default.rq_pending_overflow: 5
cluster.api_service.circuit_breakers.default.rq_retry_open: 100
```

**Key Metrics**:
- `cx_active` - Current active connections
- `cx_open` - Max connections allowed (100)
- `rq_active` - Current active requests
- `rq_pending` - Requests in queue
- `rq_pending_overflow` - **Rejected requests** (circuit open)
- `rq_retry_open` - Max retries allowed

**Alert on**:
- `rq_pending_overflow > 0` - Circuit breaker tripping
- `rq_pending > 40` - Queue filling up (80% of max_pending_requests)

---

## Circuit Breaker Pattern

**Pattern**: Outlier detection and health-based ejection
**Implementation**: Envoy outlier detection
**Status**: ✅ **COMPLETE** (M2)

### What is Circuit Breaker?

Circuit breaker prevents calls to unhealthy services, allowing them time to recover. Similar to electrical circuit breakers that "open" to prevent damage.

**States**:
- **CLOSED**: Normal operation, requests flow through
- **OPEN**: Too many failures, requests immediately rejected
- **HALF-OPEN**: Testing recovery, limited requests allowed

### Implementation Details

**Location**: `deploy/envoy/envoy-config.yaml`

**Configuration** (already exists from M2):
```yaml
outlier_detection:
  consecutive_5xx: 3                # Trigger after 3 consecutive 5xx
  interval: 10s                     # Detection interval
  base_ejection_time: 30s           # Eject unhealthy host for 30s
  max_ejection_percent: 50          # Max 50% of hosts can be ejected
  enforcing_consecutive_5xx: 100    # 100% enforcement probability
  enforcing_success_rate: 100       # Enforce success rate ejection
  success_rate_minimum_hosts: 2     # Min hosts for success rate calc
  success_rate_request_volume: 10   # Min requests for success rate
  success_rate_stdev_factor: 1900   # Outlier threshold (1.9 std dev)
```

### How It Works

```
Backend Pods: [Pod-A] [Pod-B] [Pod-C]
                 │       │       │
                 ▼       ▼       ▼
            ┌────────────────────────┐
            │  Envoy Load Balancer   │
            │  (Round Robin)         │
            └───────────┬────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
    [Pod-A]        [Pod-B]        [Pod-C]
      OK             5xx            OK
                      │
                      ▼
            ┌─────────────────────┐
            │ Consecutive 5xx = 1 │
            └─────────────────────┘
                      │
                  (2 more 5xx)
                      │
                      ▼
            ┌─────────────────────┐
            │ Consecutive 5xx = 3 │
            │ → EJECT Pod-B       │
            │   for 30s           │
            └─────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  Active Pods:          │
         │  [Pod-A] [Pod-C]       │
         │  Ejected: [Pod-B]      │
         └────────────────────────┘
                      │
                  (30s later)
                      │
                      ▼
         ┌────────────────────────┐
         │  Test Pod-B health     │
         │  If OK → Re-add        │
         └────────────────────────┘
```

### Difference: Bulkhead vs Circuit Breaker

| Feature | Bulkhead | Circuit Breaker |
|---------|----------|-----------------|
| **Purpose** | Resource isolation | Fault isolation |
| **Triggers on** | Resource limits | Error rate |
| **Action** | Reject new requests | Stop calling unhealthy service |
| **Response** | HTTP 503 (queue full) | HTTP 503 (host ejected) |
| **Recovery** | Immediate (when queue clears) | Gradual (ejection time) |
| **Protects** | Current service from overload | Downstream service from traffic |

**Used together**: Bulkhead limits connections + Circuit breaker ejects unhealthy hosts.

---

## Combined Resilience Stack

Resilience Lab uses **layered resilience patterns** for defense in depth:

```
Client Request
     │
     ▼
┌─────────────────────────────────────┐
│ 1️⃣ Rate Limiting (FastAPI)          │  ← Protect from traffic spikes
│    - 60 req/min per tenant          │
│    - Redis sliding window           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2️⃣ Ingress (Traefik)                 │  ← TLS termination, routing
│    - HTTPS with self-signed cert    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3️⃣ Envoy Proxy (Resilience Layer)   │
│ ┌─────────────────────────────────┐ │
│ │ Bulkhead (Circuit Breakers)     │ │  ← Resource limits
│ │ - max_connections: 100          │ │
│ │ - max_pending_requests: 50      │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Outlier Detection               │ │  ← Health-based ejection
│ │ - consecutive_5xx: 3            │ │
│ │ - base_ejection_time: 30s       │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Retry Policy                    │ │  ← Transient failure handling
│ │ - num_retries: 2                │ │
│ │ - per_try_timeout: 2s           │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Timeout Policy                  │ │  ← Request deadline
│ │ - request_timeout: 10s          │ │
│ │ - idle_timeout: 60s             │ │
│ └─────────────────────────────────┘ │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4️⃣ Backend Services                 │
│    - API (FastAPI)                  │
│    - Payments (FastAPI)             │
└─────────────────────────────────────┘
```

### Failure Scenarios Covered

| Scenario | Protection | Response |
|----------|-----------|----------|
| Traffic spike (1000 req/s) | Rate Limiting | HTTP 429 (excess blocked) |
| Connection pool exhausted | Bulkhead | HTTP 503 (new conns rejected) |
| Backend pod crashes | Retry Policy | Retry on healthy pod (2 attempts) |
| Backend returns 5xx errors | Outlier Detection | Eject unhealthy pod for 30s |
| Slow backend response | Timeout Policy | Abort after 10s |
| Network partition | Retry + Timeout | Fast failure (2s per-try) |

---

## Testing Resilience

### Fault Injection Scripts

**Location**: `scripts/fault-inject.sh`

**Test modes**:
```bash
# 1. Inject 500 errors (test outlier ejection)
./scripts/fault-inject.sh failure

# 2. Inject 2s delay (test timeout policy)
./scripts/fault-inject.sh slow

# 3. Kill random pod (test retry + auto-recovery)
./scripts/fault-inject.sh kill

# 4. Cleanup all injections
./scripts/fault-inject.sh cleanup
```

### Monitoring During Tests

**Port-forward Envoy admin**:
```bash
kubectl port-forward -n resilience-lab svc/envoy-proxy 9901:9901
```

**Check stats**:
```bash
# Outlier detection
curl http://localhost:9901/stats | grep outlier
# Expected: ejections_enforced_total: 1 (after failure mode)

# Circuit breakers
curl http://localhost:9901/stats | grep circuit_breaker
# Expected: rq_pending_overflow > 0 (during load spike)

# Retries
curl http://localhost:9901/stats | grep retry
# Expected: upstream_rq_retry: 2+ (during kill mode)

# Timeouts
curl http://localhost:9901/stats | grep timeout
# Expected: upstream_rq_timeout: 1+ (during slow mode)
```

### Load Testing

**Test rate limiting**:
```bash
# Port-forward Traefik
kubectl port-forward -n resilience-lab svc/traefik 8080:80

# Send 65 requests in 10s (should hit limit)
for i in {1..65}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "X-Tenant: test-tenant" \
    -H "Host: resilience-lab.local" \
    http://localhost:8080/api/healthz
done | sort | uniq -c

# Expected output:
# 60 200  ← Allowed
#  5 429  ← Rate limited
```

**Test bulkhead (connection pool exhaustion)**:
```bash
# Use Apache Bench (ab) or wrk to generate load
ab -n 1000 -c 150 http://localhost:8080/api/healthz

# Monitor Envoy stats
watch -n 1 'curl -s http://localhost:9901/stats | grep rq_pending_overflow'

# Expected: rq_pending_overflow > 0 when 150 concurrent > 100 max_connections
```

---

## Monitoring and Metrics

### Key Metrics to Track

**Rate Limiting** (Application-level):
- `rate_limit_allowed_total` - Requests allowed
- `rate_limit_blocked_total` - Requests blocked (429)
- `rate_limit_errors_total` - Redis errors

**Bulkhead** (Envoy):
- `circuit_breakers.default.cx_active` - Active connections
- `circuit_breakers.default.rq_pending` - Queued requests
- `circuit_breakers.default.rq_pending_overflow` - **Rejected requests**

**Circuit Breaker** (Envoy):
- `outlier_detection.ejections_active` - Currently ejected hosts
- `outlier_detection.ejections_enforced_total` - Total ejections
- `outlier_detection.ejections_consecutive_5xx` - Ejections due to errors

**Retries** (Envoy):
- `upstream_rq_retry` - Total retry attempts
- `upstream_rq_retry_success` - Successful retries
- `upstream_rq_retry_overflow` - Retries skipped (max_retries hit)

**Timeouts** (Envoy):
- `upstream_rq_timeout` - Requests timed out
- `upstream_rq_per_try_timeout` - Per-try timeouts

### Grafana Dashboards (Future - M3 DAY22+)

**Planned dashboards**:
1. **Resilience Overview**: Rate limits, circuit breakers, retries
2. **Envoy Metrics**: Connection pools, ejections, timeouts
3. **Application Health**: Request rates, error rates, latencies

---

## References

**Resilience Patterns**:
- [Circuit Breaker Pattern](https://microservices.io/patterns/reliability/circuit-breaker.html)
- [Bulkhead Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
- [Rate Limiting Algorithms](https://en.wikipedia.org/wiki/Rate_limiting)

**Envoy Documentation**:
- [Circuit Breaking](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Retry Policy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/http_routing#retry-semantics)

**Internal Docs**:
- [M2 Fault Tests](M2_FAULT_TESTS.md) - M2 resilience testing
- [Architecture](ARCHITECTURE.md) - System architecture overview
- [Deployment](DEPLOYMENT.md) - Kubernetes deployment guide

---

**Last updated**: December 05, 2025
**Milestone**: M3 (Resilience + Observability)
**Status**: In Progress (DAY 5/15)
