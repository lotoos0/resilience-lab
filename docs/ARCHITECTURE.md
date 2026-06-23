# Architecture

**Resilience Lab — v0.1.0**

*Last updated: 2026-06-23*

---

## Table of Contents

- [What This Actually Is](#what-this-actually-is)
- [System Overview](#system-overview)
- [Service Layer](#service-layer)
- [Networking & Resilience Layer](#networking--resilience-layer)
- [Data Layer](#data-layer)
- [Security Baseline](#security-baseline)
- [Deployment](#deployment)
- [Observability Stack](#observability-stack)
- [Architecture Decision Records](#architecture-decision-records)

---

## What This Actually Is

Resilience Lab is a microservices sandbox built to practice real SRE and DevOps patterns
in a controlled environment — the kind where you *deliberately* break things and then
prove the system recovers. It's not a production product. It's a learning project that
takes production seriously.

v0.1.0 is the MVP: two FastAPI services talking through Envoy, with rate limiting,
chaos injection, a full observability stack, and enough Kubernetes machinery to make
crashes interesting. Everything described in this document is **deployed and tested**
in v0.1.0 — not "planned" or "future". If something is still pending, it's labeled
explicitly.

The short version of why we made the choices we did: we started as a flat Docker Compose
experiment, realized microservices add just enough distributed-systems pain to be
educational, and kept layering real patterns on top until it became something worth
showing.

---

## System Overview

```
                          ┌───────────────┐
                          │   Internet /  │
                          │   kubectl     │
                          └──────┬────────┘
                                 │
                          ┌──────▼────────┐
                          │    Traefik    │  TLS termination, IngressRoute
                          └──────┬────────┘
                                 │
                          ┌──────▼────────┐
                          │     Envoy     │  port 10000 (traffic), 9901 (admin)
                          │  front-proxy  │  retries · circuit breaker · bulkhead
                          └──────┬────────┘
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
      ┌──────▼──────┐                        ┌──────▼──────┐
      │     API     │  port 8000             │  Payments   │  port 8001
      │   Service   │  rate limiting         │   Service   │  fault injection
      └──────┬──────┘  /pay → Payments       └──────┬──────┘
             │                                       │
      ┌──────▼──────┐                        ┌──────▼──────┐
      │    Redis    │  rate-limit counters    │  in-memory  │  temporary; see ADR-004
      └─────────────┘  (TTL 60s, ephemeral)  └─────────────┘
```

### Component Summary

| Component | Role | Status |
|-----------|------|--------|
| Traefik | TLS + ingress routing | Deployed (IngressRoute) |
| Envoy | L7 proxy, retry, circuit breaker, bulkhead | Deployed |
| API Service | Payment entry point, rate limiting | Deployed |
| Payments Service | Payment processing, fault injection | Deployed |
| Redis | Rate-limit sliding window counters | Deployed |
| PostgreSQL | Future persistence layer | Helm chart configured, not yet wired |
| Prometheus + Grafana + Loki | Observability stack | Deployed |

---

## Service Layer

### API Service

**Why it exists**: Single entry point for clients. Handles rate limiting before anything
hits the backend — if you're over quota, you find out here, not in Payments.

**Tech**: Python 3.11, FastAPI, Uvicorn — port `8000`.

**Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness/readiness probe |
| `/pay` | POST | Creates payment — proxies to Payments service |
| `/metrics` | GET | Prometheus metrics (prometheus-fastapi-instrumentator) |
| `/docs` | GET | OpenAPI spec (FastAPI auto-generated) |

**Rate limiting** — Redis-backed sliding window, implemented as Starlette middleware:
- Limit: **60 requests/minute per tenant**
- Tenant identity: `X-Tenant` request header (falls back to `"default"`)
- Window: 60s sliding (Redis sorted set with UUID entries)
- Excluded paths: `/healthz`, `/metrics` (probes and scrapers don't count)
- Over-limit response: `HTTP 429` with JSON body including limit and tenant ID
- Prometheus counters: `rl_allowed_total[tenant]`, `rl_denied_total[tenant]`
- Logs: logfmt-structured (`tenant=`, `path=`, `status=`, `count=`, `limit=`) for Loki

**Why Redis sorted set and not a simple counter**: Sliding window gives smooth
behavior under bursty traffic. A fixed-window counter lets you sneak 120 requests
across a window boundary — sorted set zcard doesn't.

**Downstream call**: `POST {PAYMENTS_URL}/process` via `httpx.AsyncClient`, timeout `5.0s`.
On `TimeoutException` → `HTTP 504`. On other `HTTPError` → `HTTP 503`.

---

### Payments Service

**Why it exists**: Isolated payment domain. Separate process, separate port,
independently deployable. Also: the service we deliberately break in chaos tests.

**Tech**: Python 3.11, FastAPI, Uvicorn — port `8001`.

**Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness/readiness probe |
| `/process` | POST | Create payment (validates, stores, returns ID) |
| `/payments/{id}` | GET | Fetch payment by UUID (404 if not found) |
| `/metrics` | GET | Prometheus metrics |

**Validation** (Pydantic, enforced at parse time):
- `amount`: `float`, must be `> 0`
- `currency`: `str`, pattern `^[A-Z]{3}$` (ISO 4217)
- `tenant_id`: `str`, defaults to `"default"`

**Fault injection** — controlled via environment variables, used in chaos tests:
- `FAIL_MODE=1` → returns `HTTP 500` on every `/process` call
- `SLOW_MODE=1` → sleeps `2s` before responding (simulates latency spike)

These two flags are how we exercise Envoy's retry and circuit breaker from a known,
repeatable starting point. See [chaos runbooks](RUNBOOKS.md).

**Storage**: Currently in-memory (`dict`). Data does not survive restarts. This is
intentional for v0.1.0 — the focus was on the infrastructure layer, not persistence.
PostgreSQL migration is tracked in [ADR-004](#adr-004-in-memory-storage-in-v010).

---

## Networking & Resilience Layer

### Envoy (Front Proxy)

Envoy sits between Traefik and the services. It handles everything the services
themselves shouldn't need to know about: retries, circuit breaking, bulkhead limits,
and emitting the detailed metrics that make chaos tests observable.

**Ports**: `10000` (HTTP listener), `9901` (admin API)

**Retry policy** (identical for API and Payments clusters):

| Parameter | Value | Why |
|-----------|-------|-----|
| `retry_on` | `5xx,reset,connect-failure,refused-stream` | Catches transient failures, not client errors |
| `num_retries` | `2` | Two retries = three total attempts |
| `per_try_timeout` | `200ms` | A slow upstream shouldn't tie up a retry slot |
| `base_interval` | `25ms` | Exponential backoff starting point |
| `max_interval` | `250ms` | Cap on jitter to avoid thundering-herd |

The 200ms per-try timeout is deliberate: SLOW_MODE injects a 2s delay, which blows
past it immediately. That's the point — we want to *see* retries fire under controlled
conditions, not watch the system silently hang.

**Circuit breaker** (bulkhead limits per cluster):

| Parameter | Value |
|-----------|-------|
| `max_connections` | 5 |
| `max_pending_requests` | 5 |
| `max_requests` | 10 |

These low numbers are intentional. This is a single-node minikube environment.
We want the breaker to trip under moderate load so we can observe it — not set limits
that only matter at scale.

**Outlier detection** (passive health checking):

| Parameter | Value |
|-----------|-------|
| `consecutive_5xx` | 3 |
| `interval` | 10s |
| `base_ejection_time` | 30s |
| `max_ejection_percent` | 50% |
| `enforcing_consecutive_5xx` | 100% |

After 3 consecutive 5xx responses in a 10s window, the upstream host is ejected for
30s. At most half the cluster is ejected at once — so one bad pod doesn't take the
whole service down.

### Traefik (Ingress)

TLS termination and IngressRoute definition. Routes `/api/*` → Envoy. The cert
directory lives at `deploy/traefik/certs/` (`.gitkeep`; populated at deploy time).

### NetworkPolicy

Default posture: **deny all ingress**. Everything is whitelisted explicitly.

6 NetworkPolicy manifests in `deploy/helm/templates/`:

| Policy | What it allows |
|--------|---------------|
| `netpol-default-deny` | Blocks all ingress by default |
| `netpol-allow-envoy` | Envoy → API and Payments |
| `netpol-allow-essentials` | DNS, health probes |
| `netpol-allow-prometheus-to-api` | Prometheus scrape → API `:8000/metrics` |
| `netpol-allow-prometheus-to-envoy-admin` | Prometheus scrape → Envoy `:9901/metrics` |
| `netpol-allow-redis` | API → Redis (rate-limit counters) |

Why this matters: default-deny forces us to be explicit about who talks to whom.
It catches "I accidentally wired Payments directly to Redis" before it becomes a
production incident.

---

## Data Layer

### Redis

Stores rate-limit sliding window counters. Each key is `rate_limit:{tenant_id}`,
a Redis sorted set with UUID members and Unix-timestamp scores.

- Not persisted (`emptyDir` in Kubernetes — by design, counters are ephemeral)
- No auth, no replication needed for this use case
- TTL: 60s per key (matches the rate-limit window)
- Resource limits: `cpu: 250m / 256Mi` (limit), `cpu: 50m / 64Mi` (request)

We chose a plain Deployment + Service over the Bitnami Redis subchart because
we don't need persistence, auth, or Sentinel. The Bitnami chart brings ~30 extra
values for features we'd explicitly turn off anyway.

### PostgreSQL

Helm dependency configured, but the services don't use it yet. The schema below
is the target for the next iteration:

```sql
CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amount     DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    currency   CHAR(3)        NOT NULL,
    tenant_id  VARCHAR(255)   NOT NULL,
    status     VARCHAR(50)    NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP      NOT NULL DEFAULT NOW(),
    metadata   JSONB
);

CREATE INDEX idx_payments_tenant_id  ON payments(tenant_id);
CREATE INDEX idx_payments_status     ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
```

Current state: `payments_store: Dict[str, Dict[str, Any]]` in Payments service.
Survives until the pod restarts. See [ADR-004](#adr-004-in-memory-storage-in-v010).

---

## Security Baseline

### Container Hardening

Applied in both Dockerfiles:

- `USER appuser` — non-root, dedicated user
- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capDrop: [ALL]`
- `--no-cache-dir` on pip installs (smaller image, no stale cache)

### Kubernetes Security

- NetworkPolicy default-deny (see above)
- `runAsNonRoot: true` in pod security context
- Trivy image scanning runs in CI on every build

### Application Security

- Pydantic validation on all inputs at the service boundary
- No secrets hardcoded — environment variables only (`.env.mcp.example` for reference)
- Rate limiting at the API layer (60 req/min/tenant) limits abuse surface

### Not Yet Implemented

- mTLS between services (would require service mesh — Envoy is a front proxy, not a sidecar in this setup)
- OAuth2/JWT authentication (the `X-Tenant` header is a placeholder)
- Secrets manager integration (K8s Secrets for now)

---

## Deployment

### Local — Docker Compose

```
make dev
```

Starts API, Payments, and Redis. No Envoy, no Traefik, no Prometheus in Compose —
those live in Kubernetes. Good for fast iteration on service logic.

### Kubernetes — Helm

Single parent chart (`deploy/helm/Chart.yaml`, version `0.1.0`) with two subcharts:

```
deploy/helm/
├── Chart.yaml          # parent, version 0.1.0
├── values.yaml         # production defaults
├── values-dev.yaml     # minikube overrides (local images, pullPolicy: IfNotPresent)
├── values-chaos.yaml   # chaos test overrides (FAIL_MODE, SLOW_MODE)
└── charts/
    ├── api/            # API service subchart
    └── payments/       # Payments service subchart
```

**Replica counts and scaling**:

| Service | Default replicas | HPA min | HPA max | Scale-up trigger |
|---------|-----------------|---------|---------|-----------------|
| API | 2 | 2 | 5 | CPU > 70% or memory > 80% |
| Payments | 2 | 1 | 3 | CPU > 70% or memory > 80% |
| Envoy | 1 | — | — | No HPA (single proxy) |

**Pod Disruption Budgets**:

| Service | `minAvailable` |
|---------|---------------|
| API | 1 |
| Payments | 1 |
| Envoy | 1 |

PDB ensures at least one pod survives voluntary disruptions (node drains, upgrades).
Under a 2-replica default, this means a drain will wait before evicting the second pod.

**Probes** (API service, same pattern for Payments):
- Startup: `GET /healthz`, failureThreshold 30 × 10s (5 min to come up)
- Liveness: `GET /healthz`, initialDelay 10s, period 10s, timeout 5s, failureThreshold 3
- Readiness: `GET /healthz`, initialDelay 5s, period 5s, timeout 3s

**Images**: Built and pushed to `ghcr.io/lotoos0/resilience-lab-{api,payments}` via CI.
Tagged by git SHA on every push; additionally tagged `v*` on version tags.

---

## Observability Stack

### Prometheus

3 ServiceMonitors (API, Payments, Envoy admin port).

Recording rules in `deploy/prometheus/rules.yaml` — 3 groups, 18 rules total:

**`envoy_metrics`**: request rate per cluster, 5xx error rate, p95 latency,
active upstream connections, retry rate, outlier ejection rate, bulkhead overflow rate.

**`api_metrics`**: HTTP request rate, HTTP 5xx error rate, rate-limit allowed/denied
counters (from custom `rl_allowed_total` / `rl_denied_total` Prometheus counters).

**`system_health`**: pod availability count, total pods, availability ratio.

3 alert rules: `HighErrorRate`, `APIDown`, `PrometheusTargetDown`.

### Grafana

2 dashboards shipped in `deploy/helm/dashboards/`:

- **System Overview** — pod availability, request throughput, error rate
- **Resilience** (Traffic & Latency) — retry rate, outlier ejections, rate-limit
  denials, bulkhead overflow, p95 latency

Dashboards are provisioned via ConfigMap (Helm templates), not clicked together in UI —
so they survive pod restarts and are version controlled.

### Loki + Promtail

Centralized log aggregation. Rate-limit middleware emits logfmt-structured logs:

```
rate_limit_check tenant=acme path=/pay status=denied count=61 limit=60
```

Filterable in Loki with LogQL:
```logql
{app="api"} | logfmt | tenant="acme" | status="denied"
```

### Why This Much Observability for a Learning Project?

Because the point of the project is resilience patterns — and you can't know if
your retry policy is doing anything without metrics. The Grafana panel showing
`envoy:retries:rate5m` climbing during a SLOW_MODE chaos run is what validates
the architecture, not the code itself.

---

## Architecture Decision Records

### ADR-001: Microservices

**Status**: Accepted

**Decision**: Two separate services (API + Payments) with independent deployment,
dedicated ports, and separate data stores.

**Why**: A monolith would work fine at this scale. The microservices split is
deliberate — it creates real distributed systems problems (inter-service latency,
partial failures, independent scaling) that are the whole point of the project.

**Trade-offs**:
- Operational complexity increases (two health checks, two image builds, two Helm subcharts)
- Circuit breaking and retry logic become meaningful, not theoretical
- End-to-end request tracing across service boundaries is a real problem to solve

---

### ADR-002: FastAPI

**Status**: Accepted

**Decision**: FastAPI for both services.

**Why**: Auto-generated OpenAPI docs (`/docs`) come for free. Pydantic validation
at the model level means we don't write `if amount <= 0: raise` manually. Async
support means `httpx.AsyncClient` in the API gateway doesn't block a thread per
in-flight request to Payments.

**Trade-offs**:
- Uvicorn + FastAPI is not the leanest stack (compare to plain WSGI) — acceptable here
- Async Python has an initial mental model cost; it earns its keep at the I/O layer

---

### ADR-003: Envoy as Front Proxy (not Sidecar)

**Status**: Accepted

**Decision**: One Envoy instance as a dedicated front proxy, not as a sidecar
injected into every pod.

**Why**: A full service mesh (Istio, Linkerd) would give us mTLS, per-pod telemetry,
and more granular traffic control — but also a significant operational overhead for
a single-node minikube cluster. A front proxy gives us retry, circuit breaking, and
Envoy metrics (which are excellent) without the complexity of a mesh control plane.

**What we give up**: mTLS between API and Payments. The traffic inside the cluster
is unencrypted service-to-service. Acceptable for a sandboxed learning environment.

**If this were production**: We'd move to Istio sidecars and add mTLS. The Envoy
config knowledge transfers directly — same filter chains, same retry policy syntax.

---

### ADR-004: In-Memory Storage in v0.1.0

**Status**: Accepted (Temporary)

**Decision**: Payments service uses an in-memory Python `dict` as its store.

**Why**: v0.1.0 focused on the infrastructure layer — networking, resilience patterns,
observability, CI/CD, security hardening. Adding a PostgreSQL ORM and migration tooling
would have been real work that delayed the things we actually wanted to learn.

**Consequences**:
- Payments data is lost on every pod restart or scale event
- This is fine for chaos testing (we don't care about specific payment IDs)
- The PostgreSQL schema is designed and the Helm dependency is wired — migration is
  the first task in the next iteration

**Migration**: Add SQLAlchemy async, run Alembic migration creating the `payments`
table (schema in [Data Layer](#data-layer)), switch `payments_store` dict to
repository pattern. The API surface doesn't change.

---

### ADR-005: Plain Redis Deployment (not Bitnami subchart)

**Status**: Accepted

**Decision**: Redis is deployed as a plain `Deployment` + `Service` in the Helm
templates, not as a Bitnami subchart dependency.

**Why**: The rate-limit middleware needs exactly one thing from Redis: an atomic
sorted-set store for sliding-window counters. The counters are ephemeral by design
(TTL = 60s, same as the window). No persistence, no auth, no replication, no Sentinel.
The Bitnami chart has ~30 configurable parameters for features we'd explicitly disable.
A 30-line Deployment template is more honest about what we actually need.

---

### ADR-006: Docker Compose for Local Dev, Kubernetes for Everything Else

**Status**: Accepted

**Decision**: Docker Compose (`make dev`) runs API + Payments + Redis locally.
Kubernetes is the only environment where the full stack (Envoy, Traefik, Prometheus,
Grafana, Loki) is deployed.

**Why**: Running a full kube-prometheus-stack and Envoy in Docker Compose would
require significant extra config with no benefit for day-to-day service development.
Compose is for fast iteration on service logic. Kubernetes is for integration testing
and chaos work.

**Trade-offs**:
- Local environment doesn't match production exactly (no Envoy, no NetworkPolicy)
- Rate limiting still works locally (Redis in Compose)
- For chaos tests, you need minikube — `make dev` is not enough

---

*Architecture reflects the state of v0.1.0 (released 2026-06-23).*
*Next iteration target: PostgreSQL persistence, request tracing (Jaeger/Tempo).*
