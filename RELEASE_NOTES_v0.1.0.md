# v0.1.0 — Resilience Lab MVP

## Overview

This is the first real release. Not "first commit" first — that was months ago — but
first "it actually works end to end" first.

v0.1.0 is the MVP: two FastAPI services talking to each other through Envoy, with rate
limiting, observability, chaos testing, and enough Kubernetes machinery that you can
break things deliberately and watch the system respond. Everything that was promised in
the milestone plan is here. It took longer than planned (it always does), but nothing
was cut to make the deadline — the scope held.

This is a learning project, built to practice real SRE and DevOps patterns in a
controlled environment before they matter in production. It's also meant to be a
portfolio piece that shows working code, not just architecture diagrams.

---

## What's New

This is the initial release, so everything is new. The highlights by layer:

**Services**
- **API service** — FastAPI, Python 3.11, per-tenant rate limiting backed by Redis,
  Prometheus metrics via `prometheus-fastapi-instrumentator`
- **Payments service** — FastAPI, PostgreSQL-backed, structured logging with tenant
  context per request

**Networking & resilience**
- **Envoy front-proxy** — retry with per-try timeout (200ms) and exponential backoff,
  outlier ejection, circuit breaker, bulkhead limits — all tuned and stress-tested
- **Traefik ingress** — TLS termination, routes to Envoy
- **HPA + PDB** — auto-scaling and disruption budget validated under load

**Observability**
- **Prometheus** — ServiceMonitors for API and Envoy, recording rules for all key
  signals (request rate, error rate, p95 latency, retry rate, ejection rate, 429s,
  bulkhead overflow)
- **Alert rules** — HighErrorRate, APIDown, PrometheusTargetDown
- **Grafana dashboards** — System Overview and Traffic & Latency (panels for retries,
  outlier ejections, rate-limit denials, bulkhead overflow, p95 latency)
- **Loki + Promtail** — centralized log aggregation with LogQL examples and tenant
  filtering

**Chaos engineering**
- **Latency injection** — 300ms `tc netem` delay on Payments via `fault-inject.sh`,
  Grafana evidence captured
- **Pod kill** — auto-recovery tested (~15s), HPA and PDB behavior documented
- **Runbooks** — chaos-pod-kill, chaos-latency-injection, rollback-vs-recover

**Infrastructure**
- **Helm chart** — single parent chart with subchart structure, `values-dev.yaml`
  for local minikube
- **CI/CD** — GitHub Actions: lint → unit tests → integration tests → Docker build →
  push to GHCR; runs on every PR and push to develop/main
- **Security baseline** — `runAsNonRoot`, `readOnlyRootFilesystem`, `capDrop: ALL`,
  no privilege escalation; Trivy scanning in CI

---

## Improvements

Not applicable — this is the initial release.

---

## Bug Fixes

Fixes made during development that are included in this release:

- Fixed Grafana HTTP status codes panel query returning incorrect breakdown
- Fixed rate-limit k6 smoke test targeting an excluded endpoint (tests were always
  green for the wrong reason)
- Fixed `GET /` return type annotation causing response validation warnings (#63)
- Patched OpenSSL CVE-2026-45447 via `apt upgrade` in both Docker images
- Patched Starlette CVE-2026-48818 and CVE-2026-54283 (bumped to 1.3.1)
- Fixed `values-dev.yaml` pointing at wrong Payments image tag in minikube (#70)

---

## Breaking Changes

None — this is the first release.

---

## Upgrade Notes

Fresh install only. No migration needed.

```bash
# Local (Docker Compose)
git clone https://github.com/lotoos0/resilience-lab.git
cd resilience-lab
make dev

# Kubernetes (minikube)
eval $(minikube docker-env)
docker build -f services/api/Dockerfile -t resilience-lab-api:local .
docker build -f services/payments/Dockerfile -t resilience-lab-payments:local .
make helm-deps
make helm-up-dev
```

For full deployment instructions: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
