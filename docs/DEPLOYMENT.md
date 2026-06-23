# Deployment

**Resilience Lab — v0.1.0**

*Last updated: 2026-06-23*

---

## Table of Contents

- [Two Environments, One Rule](#two-environments-one-rule)
- [Prerequisites](#prerequisites)
- [Local — Docker Compose](#local--docker-compose)
- [Kubernetes — minikube + Helm](#kubernetes--minikube--helm)
- [Images & Registry](#images--registry)
- [CI/CD Pipeline](#cicd-pipeline)
- [Chaos Testing Deployment](#chaos-testing-deployment)
- [Scripts Reference](#scripts-reference)
- [Troubleshooting](#troubleshooting)

---

## Two Environments, One Rule

There are two ways to run Resilience Lab, and they serve different purposes:

| Environment | Command | What starts | Use for |
|-------------|---------|-------------|---------|
| **Docker Compose** | `make dev` | API, Payments, PostgreSQL, Redis | Fast iteration on service code |
| **Kubernetes (minikube)** | `make helm-up-dev` | Everything above + Envoy, Traefik, Prometheus, Grafana, Loki | Integration tests, chaos work, observability |

The rule: if you're touching service logic, Compose is enough. If you're running
chaos tests or validating observability, you need Kubernetes. `make dev` won't
give you Envoy retry metrics — that's not a bug, it's a deliberate split.

---

## Prerequisites

### For Docker Compose

- Docker 24+
- Docker Compose v2+
- `make`

### For Kubernetes

Everything above, plus:

- [minikube](https://minikube.sigs.k8s.io/) — local cluster
- [kubectl](https://kubernetes.io/docs/tasks/tools/) — configured against minikube
- [Helm](https://helm.sh/) 3+

The Helm chart targets minikube. Running it against a remote cluster works, but
`values-dev.yaml` uses locally built images (`pullPolicy: IfNotPresent`) — you'd
need to adjust image tags and registry for anything beyond a laptop.

---

## Local — Docker Compose

### Quick Start

```fish
git clone https://github.com/lotoos0/resilience-lab.git; cd resilience-lab; make dev
```

That's it. Docker Compose starts 4 services in dependency order:

1. **PostgreSQL** (postgres:16) — waits for `pg_isready`
2. **Redis** (redis:7-alpine) — waits for `redis-cli ping`
3. **Payments** — waits for its own `/healthz`
4. **API** — waits for Payments healthcheck, then comes up last

Startup takes ~30s on a cold run (image pulls aside). The `depends_on: condition:
service_healthy` chain means you won't hit a partially started stack.

### Ports

| Service | Port |
|---------|------|
| API | `8000` |
| Payments | `8001` |
| PostgreSQL | `5432` |
| Redis | `6379` |

### Verify

```fish
curl http://localhost:8000/healthz; curl http://localhost:8001/healthz
```

Expected: `{"status":"healthy","service":"api"}` and `{"status":"healthy","service":"payments"}`.

### Useful Compose Commands

```fish
make ps          # status of all containers
make logs        # tail all logs
make logs-api    # tail API only
make logs-payments
make down        # stop (keep volumes)
make clean       # stop + remove volumes + docker system prune
make restart     # make down && make dev
```

### One Honest Note About PostgreSQL in Compose

Docker Compose starts a PostgreSQL container and the services receive a
`DATABASE_URL` env var. However, the Payments service uses in-memory storage
and ignores it entirely. The container is there as infrastructure groundwork
and to keep the Compose environment consistent with the Helm chart. See
[ADR-004 in ARCHITECTURE.md](ARCHITECTURE.md#adr-004-in-memory-storage-in-v010).

---

## Kubernetes — minikube + Helm

### First-Time Setup

**Step 1** — start minikube and point Docker at its daemon:

```fish
minikube start; eval (minikube docker-env)
```

The `eval` is essential. Without it, `docker build` writes images to the host
daemon, not to minikube's — and your pods get `ImagePullBackOff` because they
look for images that don't exist inside the cluster.

**Step 2** — build images locally:

```fish
docker build -f services/api/Dockerfile -t resilience-lab-api:local .
docker build -f services/payments/Dockerfile -t resilience-lab-payments:local .
```

`values-dev.yaml` uses `tag: local` and `pullPolicy: IfNotPresent`, so Kubernetes
picks up these images directly without needing a registry.

**Step 3** — generate TLS certs for Traefik:

```fish
./scripts/generate-certs.sh
```

Generates a self-signed RSA 2048 cert (365-day validity) for `resilience-lab.local`
into `deploy/traefik/certs/`. These are gitignored — don't commit them.

**Step 4** — install the Helm chart:

```fish
make helm-deps; make helm-up-dev
```

`helm-deps` resolves the two subcharts (`api`, `payments`) before install.
`helm-up-dev` runs:

```
helm upgrade --install resilience-lab deploy/helm/ \
  --values deploy/helm/values-dev.yaml \
  --namespace resilience-lab \
  --create-namespace
```

### What Helm Deploys

The parent chart (`deploy/helm/`, version `0.1.0`) deploys:

| Resource | Count | Notes |
|----------|-------|-------|
| Deployments | 3 | API, Payments, Envoy |
| Services | 3 | ClusterIP for each |
| HPAs | 2 | API (2→5), Payments (1→3) |
| PDBs | 3 | minAvailable: 1 each |
| NetworkPolicies | 6 | default-deny + explicit allows |
| ConfigMap (Envoy config) | 1 | `envoy-config` |
| ConfigMaps (Grafana dashboards) | 2 | System Overview, Resilience |
| Redis Deployment + Service | 1+1 | Plain, no Bitnami subchart |

**Dev overrides** (`values-dev.yaml`):
- `api.replicaCount: 1` (saves minikube resources)
- `payments.replicaCount: 1`
- Local image tags (`pullPolicy: IfNotPresent`)
- `LOG_LEVEL: DEBUG`

### Verify the Deployment

```fish
kubectl get pods -n resilience-lab; kubectl get hpa -n resilience-lab
```

Run Helm tests (connection smoke tests baked into the chart):

```fish
make helm-test
```

Access via Traefik (add `resilience-lab.local` to `/etc/hosts` pointing at
`$(minikube ip)` first):

```fish
curl -k https://resilience-lab.local/api/healthz
```

Or use `health-loop.sh` for a continuous stream of requests during chaos testing:

```fish
./scripts/health-loop.sh
```

Fires a request every 200ms to `localhost:8080/api/healthz` and prints the
HTTP status code — useful for watching the system recover in real time.

### Day-to-Day Helm Operations

```fish
# Upgrade after code change (rebuild image first)
make helm-up-dev

# Rollback to previous revision
make rollback-1

# Rollback to specific revision N
make rollback-2

# Check release history
helm history resilience-lab -n resilience-lab

# Tear everything down
make helm-down
```

### Observability Stack

Prometheus, Grafana, and Loki are not in the main Helm chart — they're deployed
separately via their own Helm charts (kube-prometheus-stack, Loki stack). See
[docs/observability.md](observability.md) for the full setup walkthrough.

ServiceMonitors at `deploy/prometheus/servicemonitor-*.yaml` connect Prometheus
to the API, Payments, and Envoy admin endpoints once the stack is up.

---

## Images & Registry

### Build

Both images are based on `python:3.11-slim`. The builds run from the repo root
(context is `.`) so they can access `requirements.txt` and `services/`.

**API image** (`services/api/Dockerfile`):
- Installs all dependencies from `requirements.txt`
- Copies `services/api/`
- Runs as `appuser` (non-root)
- Port: `8000`

**Payments image** (`services/payments/Dockerfile`):
- Same as API, but also installs `iproute2`
- `iproute2` ships the `tc` command — without it, `fault-inject.sh latency`
  fails with a missing binary. This is why it's in the production image and
  not just a dev dependency.
- Port: `8001`

Security baseline applied in both:
- `RUN apt-get upgrade -y` — patches OS packages at build time (picked up CVEs
  like OpenSSL CVE-2026-45447)
- `pip install --no-cache-dir` — no pip cache left in the layer
- `USER appuser` — non-root at runtime
- `HEALTHCHECK` — Docker-native probe on `/healthz`

### Registry

Images are pushed to GitHub Container Registry:

```
ghcr.io/lotoos0/resilience-lab-api
ghcr.io/lotoos0/resilience-lab-payments
```

Tags:
- `<git-sha>` — every push to `main` or `develop`
- `<version>` (e.g. `v0.1.0`) — every `v*` tag push
- `latest` — always updated alongside the SHA/version tag

Pull images without authentication (packages are public):

```fish
docker pull ghcr.io/lotoos0/resilience-lab-api:latest
```

---

## CI/CD Pipeline

Two GitHub Actions workflows in `.github/workflows/`:

### CI (`ci.yml`) — every push and PR to `main`/`develop`

Runs 4 jobs, in this order:

```
lint ──┬── test ──┬── integration-test
       │          │
       └──────────┴── build
```

| Job | What it does |
|-----|-------------|
| `lint` | `ruff check services/` |
| `trivy-fs` | Trivy filesystem scan (CRITICAL + HIGH), results to GitHub Security tab |
| `test` | Unit tests (`pytest -m "not integration"`) with real postgres:16 + redis:7-alpine sidecar services, coverage → Codecov |
| `integration-test` | Spins up full Docker Compose stack, waits for healthy, runs `pytest -m integration`, tears down |
| `build` | Builds both images, runs Trivy image scan (exit-code 1 on CRITICAL/HIGH unfixed CVEs) |

**Note on CI service containers**: The test job spins up postgres:16 and
redis:7-alpine — but the unit tests mock both (Redis via `unittest.mock.Mock`,
PostgreSQL is unused entirely). The containers are there as groundwork for
future integration-level unit tests, not because anything currently requires
a live connection.

**Why integration tests are separate**: They need Docker Compose, which means
building images, which takes 2–3 minutes. Keeping them in a separate job lets
`lint` and `test` fail fast without waiting for Docker.

### CD (`cd.yml`) — push to `main`/`develop`, or `v*` tag

One job: `build-and-push`.

Determines the image tag:
- If triggered by a `v*` tag → tag = version string (e.g. `v0.1.0`)
- Otherwise → tag = `$GITHUB_SHA`

Builds both images, tags them, pushes SHA/version tag + `latest` to GHCR.

**No automatic Kubernetes deploy**: The deploy step in `cd.yml` is commented
out. I build and push automatically, but I trigger `helm upgrade` manually.
Until there's a staging cluster with a proper kubeconfig secret, automating
the K8s deploy would mean committing cluster credentials — not worth it.

---

## Chaos Testing Deployment

Chaos tests run against the Kubernetes cluster. Docker Compose is not enough
because you need Envoy to observe retries, ejections, and circuit breaking.

### Before Running Chaos

Make sure you're running with dev values:

```fish
make helm-up-dev
```

### Latency Injection

Injects 300ms `tc netem` delay on all Payments pods:

```fish
./scripts/fault-inject.sh latency
```

This requires `NET_ADMIN` capability and `iproute2` in the container. If you
get "Operation not permitted", apply chaos overrides first:

```fish
helm upgrade resilience-lab deploy/helm/ \
  -n resilience-lab \
  -f deploy/helm/values-dev.yaml \
  -f deploy/helm/values-chaos.yaml
```

`values-chaos.yaml` adds `NET_ADMIN` to the Payments pod security context.
On some clusters this alone isn't enough — `runAsRoot: true` may be needed
(it's in the file, commented as Stage 2).

### FAIL_MODE and SLOW_MODE

Inject via env var — no pod restart needed:

```fish
./scripts/fault-inject.sh failure   # FAIL_MODE=1 → Payments returns 500
./scripts/fault-inject.sh slow      # SLOW_MODE=1 → Payments delays 2s
./scripts/fault-inject.sh kill      # deletes one payments pod
```

### Cleanup

Always clean up after a chaos run:

```fish
./scripts/fault-inject.sh cleanup
```

Removes `FAIL_MODE` and `SLOW_MODE` env vars and `tc netem` rules.
If you applied `values-chaos.yaml`, restore baseline:

```fish
helm upgrade resilience-lab deploy/helm/ -n resilience-lab -f deploy/helm/values-dev.yaml
```

See [runbooks/chaos-latency-injection.md](runbooks/chaos-latency-injection.md)
and [runbooks/chaos-pod-kill.md](runbooks/chaos-pod-kill.md) for full step-by-step
procedures with expected Grafana outputs.

---

## Scripts Reference

| Script | What it does |
|--------|-------------|
| `fault-inject.sh latency` | 300ms `tc netem` delay on all Payments pods |
| `fault-inject.sh failure` | `FAIL_MODE=1` — Payments returns HTTP 500 |
| `fault-inject.sh slow` | `SLOW_MODE=1` — Payments delays 2s |
| `fault-inject.sh kill` | Deletes one Payments pod |
| `fault-inject.sh cleanup` | Removes all injections |
| `generate-certs.sh` | Self-signed RSA 2048 cert for `resilience-lab.local` (365 days) |
| `health-loop.sh` | Fires requests every 200ms, prints HTTP status — live recovery monitor |

`pg_backup.sh` and `redis_backup.sh` are empty stubs — PostgreSQL isn't wired
up yet, and Redis counters are ephemeral by design (TTL 60s). Nothing worth
backing up at this stage.

---

## Troubleshooting

For common issues specific to Helm field ownership conflicts, minikube image
visibility, Prometheus scrape failures, and observability targets, there are
dedicated troubleshooting docs in `docs/troubleshooting/`. Short versions below.

### Pod stuck in `ImagePullBackOff`

Almost always means you built the image outside minikube's Docker daemon:

```fish
eval (minikube docker-env)
docker build -f services/api/Dockerfile -t resilience-lab-api:local .
docker build -f services/payments/Dockerfile -t resilience-lab-payments:local .
make helm-up-dev
```

### Helm upgrade fails with field ownership error

Happens when `kubectl` and Helm both manage the same field. Fix:

```fish
helm upgrade resilience-lab deploy/helm/ -n resilience-lab \
  -f deploy/helm/values-dev.yaml --force-conflicts
```

See [runbooks/TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md](runbooks/TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md).

### Pod not starting — general

```fish
kubectl get pods -n resilience-lab
kubectl describe pod <pod-name> -n resilience-lab
kubectl logs <pod-name> -n resilience-lab
kubectl get events -n resilience-lab --sort-by='.lastTimestamp'
```

### Service unreachable

```fish
kubectl get svc -n resilience-lab
kubectl get endpoints -n resilience-lab
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# then inside: wget -O- http://resilience-lab-api:8000/healthz
```

### Envoy not scraping in Prometheus

Check the ServiceMonitor label selector matches the Prometheus instance and
that the Envoy admin port (9901) is accessible. See
[runbooks/TROUBLESHOOTING_PROMETHEUS_SCRAPE.md](runbooks/TROUBLESHOOTING_PROMETHEUS_SCRAPE.md).

---

*For architecture decisions behind deployment choices, see [ARCHITECTURE.md](ARCHITECTURE.md).*
