[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml)
[![CD](https://github.com/lotoos0/resilience-lab/actions/workflows/cd.yml/badge.svg)](https://github.com/lotoos0/resilience-lab/actions/workflows/cd.yml)
[![codecov](https://codecov.io/gh/lotoos0/resilience-lab/branch/main/graph/badge.svg)](https://codecov.io/gh/lotoos0/resilience-lab)
[![Security](https://img.shields.io/badge/security-Trivy-blue)](https://github.com/lotoos0/resilience-lab/security/code-scanning)

![Resilience Lab banner](docs/img/resilience_lab_banner.gif)

# Resilience Lab

**A Kubernetes sandbox for practicing cloud-native failure patterns before they hit production.**

This project gives you a realistic microservices environment — FastAPI, PostgreSQL, Redis — with observability, rate limiting, and resilience policies already configured. The idea is simple: break things here on purpose,
learn how they fail, and carry that knowledge to production. Not a toy demo. Not a tutorial app.
A working lab you can actually deploy and run experiments on.

---

## Why this project exists

Most demo apps only show the happy path. Resilience Lab is built for the opposite case.

It helps you practice what happens when services slow down, crash, overload Redis, hit rate limits,
or start returning 5xx errors — with real Kubernetes, Envoy policies, metrics, logs, dashboards,
alerts, and runbooks in place.

Use it to practice DevOps/SRE workflows, test failure scenarios, and show a working Kubernetes-based project in your portfolio.

---

## What's in the box

- **API + Payments services** — FastAPI, Python 3.11, Prometheus metrics, rate limiting
- **Networking layer** — Traefik ingress → Envoy front-proxy (retry, timeout, circuit breaker)
- **Observability** — Prometheus + Grafana dashboards (system overview, traffic & latency), alert rules
- **Kubernetes-ready** — Helm charts, HPA, PDB, NetworkPolicy, non-root security baseline
- **CI/CD** — GitHub Actions: lint → test → integration → build → publish to GHCR
- **Fault injection** — scripts for failure, slow, and kill scenarios

---

## Quick Start

| Goal | Command |
|------|---------|
| Run the app locally | `make dev` |
| Run resilience experiments in Kubernetes | `make helm-up-dev` |

### Local (Docker Compose)

```bash
git clone https://github.com/lotoos0/resilience-lab.git
cd resilience-lab
make dev
```

Services will be up at:
- API: http://localhost:8000
- Payments: http://localhost:8001

```bash
curl http://localhost:8000/healthz   # {"status":"healthy","service":"api"}
curl http://localhost:8001/healthz   # {"status":"healthy","service":"payments"}
make down                            # stop everything
```

**Prerequisites:** Docker 24+, Docker Compose v2+, Python 3.11+, Make.

---

## Kubernetes (Helm)

```bash
# Create a local cluster — k3d is the recommended option
k3d cluster create resilience-cluster --api-port 6550 --servers 1 --agents 2 --port "8080:80@loadbalancer"

# Deploy
make helm-deps
make helm-up-dev

# Verify
kubectl get pods -n resilience-lab

# Tear down
make helm-down
```

For minikube/kind, custom values, and troubleshooting: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Architecture

```
        User / Browser
               │
               ▼
       ┌──────────────┐
       │   Traefik    │  ← HTTPS ingress (TLS termination)
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │    Envoy     │  ← front-proxy: retry, timeout, circuit breaker
       └──────┬───────┘
              │
         ┌────┴────┐
         ▼         ▼
  ┌───────────┐ ┌───────────┐
  │    API    │ │  Payments │
  │ :8000     │ │ :8001     │
  └─────┬─────┘ └────┬──────┘
        └──────┬──────┘
               │
        ┌──────┴───────┐
        ▼              ▼
  ┌───────────┐  ┌───────────┐
  │PostgreSQL │  │  Redis    │
  └───────────┘  └───────────┘
```

Envoy sits between the ingress and your services and handles the resilience layer: failed requests are
retried automatically, slow responses get cut off before they cascade, and hosts that start returning
errors get temporarily ejected from the pool. Rate limiting lives in the API service — per tenant,
backed by Redis, so it works correctly across replicas.

---

## Current state — M3 Complete

M0–M2 done (bootstrap, CI/CD, Helm, networking layer, resilience primitives). M3 shipped:

- ✅ Rate limiting — Redis-backed, per-tenant, k6 validated
- ✅ Prometheus metrics + ServiceMonitors + recording rules
- ✅ Alert rules (HighErrorRate, APIDown, PrometheusTargetDown)
- ✅ Grafana: System Overview + Traffic & Latency dashboards
- ✅ Loki + Promtail log aggregation, LogQL in Grafana Explore
- ✅ Grafana resilience dashboard (rate limiting / circuit breaker panels)

Up next — **M4:** security audit, chaos scenarios, and the next stable release.

---

## Testing resilience

Requires the Helm deployment to be running (`make helm-up-dev`).

```bash
# Inject failures (triggers outlier detection)
./scripts/fault-inject.sh failure

# Inject latency (triggers per-try timeouts)
./scripts/fault-inject.sh slow

# Kill a pod (tests retry + auto-recovery)
./scripts/fault-inject.sh kill

# Cleanup
./scripts/fault-inject.sh cleanup
```

Watch Envoy stats during a test:

```bash
kubectl port-forward -n resilience-lab svc/envoy-proxy 9901:9901
curl http://localhost:9901/stats | grep -E 'outlier|retry|timeout'
```

---

## Development

```bash
make install      # install dev dependencies
make test         # run all tests (requires: make dev)
make test-unit    # unit tests only (no services needed)
make lint         # ruff
make help         # full list of targets
```

Coding standards, project structure, and onboarding: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

---

## Docs

| Doc | What's in it |
|-----|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, ADRs, design patterns |
| [Development](docs/DEVELOPMENT.md) | Setup, structure, coding standards |
| [Deployment](docs/DEPLOYMENT.md) | Full Helm deployment guide |
| [Observability](docs/observability.md) | Prometheus, Grafana, Loki, LogQL |
| [M3 Resilience Patterns](docs/M3_RESILIENCE_PATTERNS.md) | Rate limiting, load tests |
| [Runbooks](docs/runbooks/README.md) | Incident runbooks |
| [Retrospectives](docs/RETROSPECTIVES.md) | Milestone retrospectives |
| [Contributing](CONTRIBUTING.md) | PR process, commit format |

---

## License

MIT — see [LICENSE](LICENSE).
