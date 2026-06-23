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
| **Kubernetes (minikube)** | `make helm-up-dev` | API, Payments, Redis, HPAs/PDBs/NetworkPolicies, Grafana dashboard ConfigMaps | Integration tests, chaos work, observability |

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
`values-dev.yaml` mixes one pinned GHCR image for API with one local image for
Payments (`pullPolicy: IfNotPresent`). For anything beyond a laptop, use pushed
registry tags for both services. Tiny footgun, big `ImagePullBackOff` energy.

---

## Local — Docker Compose

### Quick Start

```fish
git clone https://github.com/lotoos0/resilience-lab.git; cd resilience-lab; make dev
```

That's it. Docker Compose starts 4 services in dependency order:

1. **PostgreSQL** (postgres:16) — waits for `pg_isready`
2. **Redis** (redis:7-alpine) — waits for `redis-cli ping`
3. **Payments** — waits for PostgreSQL and Redis healthchecks
4. **API** — waits for PostgreSQL, Redis, and Payments healthchecks; comes up last

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
`DATABASE_URL` env var. However, v0.1.0 service code does not open a PostgreSQL
connection: Payments uses in-memory storage, and API does not use a database
client at all. The container is there as infrastructure groundwork and to keep
local service configuration close to the Kubernetes env vars. See [ADR-004 in
ARCHITECTURE.md](ARCHITECTURE.md#adr-004-in-memory-storage-in-v010).

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

**Step 2** — build the local image that `values-dev.yaml` actually references:

```fish
docker build -f services/payments/Dockerfile -t resilience-lab-payments:local .
```

`values-dev.yaml` uses different strategies per service:
- **Payments**: `repository: resilience-lab-payments`, `tag: local`, `pullPolicy: IfNotPresent` — picks up the locally built image above.
- **API**: `repository: ghcr.io/lotoos0/resilience-lab-api`, `tag: 8b86f3d`. With `pullPolicy: IfNotPresent`, minikube reuses that exact image if it already exists locally; otherwise it pulls from GHCR.

If you want a fully local API build too, override both repository and tag:

```fish
docker build -f services/api/Dockerfile -t api:local .
helm upgrade --install resilience-lab deploy/helm/ \
  --values deploy/helm/values-dev.yaml \
  --namespace resilience-lab \
  --create-namespace \
  --set api.image.repository=api \
  --set api.image.tag=local
```

**Step 3** — optional: generate TLS certs for the separate Traefik IngressRoute:

```fish
./scripts/generate-certs.sh
```

Generates a self-signed RSA 2048 cert (365-day validity) for `resilience-lab.local`
into `deploy/traefik/certs/`. These are gitignored — don't commit them. This
script only creates files; it does not create the Kubernetes TLS Secret or apply
`deploy/traefik/ingressroute.yaml`.

**Step 4** — install the Helm chart:

```fish
make helm-up-dev
```

`helm-up-dev` depends on `helm-deps`, so it resolves the two subcharts (`api`,
`payments`) before install. Running `make helm-deps` manually first is fine, but
it is belt-and-suspenders territory; useful only if your belt enjoys paperwork.
`helm-up-dev` runs:

```
helm upgrade --install resilience-lab deploy/helm/ \
  --values deploy/helm/values-dev.yaml \
  --namespace resilience-lab \
  --create-namespace
```

If you generated Traefik certs in Step 3, wire them into Kubernetes after
`helm-up-dev` creates the namespace:

```fish
kubectl create secret tls resilience-lab-tls \
  -n resilience-lab \
  --cert=deploy/traefik/certs/tls.crt \
  --key=deploy/traefik/certs/tls.key \
  --dry-run=client -o yaml | kubectl apply -f -
```

**Step 5** — optional but required for Envoy-based resilience checks:

```fish
kubectl apply -f deploy/envoy/
```

Envoy is not part of the Helm chart today. The chart prepares some Envoy-facing
policy/PDB objects, but the actual Envoy ConfigMap, Deployment, and Service live
under `deploy/envoy/`. Yes, that split is a little spicy; at least now the docs
admit it out loud.

### What Helm Deploys

The parent chart (`deploy/helm/`, version `0.1.0`) renders 20 main resources:

| Resource | Count | Notes |
|----------|-------|-------|
| Deployments | 3 | API, Payments, Redis |
| Services | 3 | API, Payments, Redis |
| HPAs | 2 | API (2→5), Payments (1→3) |
| PDBs | 3 | API, Payments, and an Envoy PDB for the separately applied Envoy deployment |
| NetworkPolicies | 7 | default-deny + explicit allows, including Envoy-facing policies |
| ConfigMaps (Grafana dashboards) | 2 | System Overview, Resilience |

Redis is a plain Deployment + Service included in the counts above; there is no
Bitnami subchart involved.

The render also includes 4 Helm test Pods. Three are simple health checks. One
legacy integration test still calls `/api/payments/test`; the current API exposes
`/pay`, so treat that test as chart debt until it is aligned. Documentation
should not sell you a unicorn with a broken curl command.

No PostgreSQL or Envoy Deployment is rendered by the Helm chart today.
`DATABASE_URL` is still present in service env vars as future groundwork, but
v0.1.0 service code does not depend on a live Kubernetes PostgreSQL pod.

**Dev overrides** (`values-dev.yaml`):
- `api.replicaCount: 1` in the Deployment template, but the API HPA has `minReplicas: 2`; once HPA reconciles, expect 2 API pods
- `payments.replicaCount: 1`
- API pinned to GHCR tag `8b86f3d`; Payments uses local tag `resilience-lab-payments:local`
- `LOG_LEVEL: DEBUG`

### Verify the Deployment

```fish
kubectl get pods -n resilience-lab; kubectl get hpa -n resilience-lab
```

Run Helm tests if you specifically want to exercise the chart hooks:

```fish
make helm-test
```

Remember the legacy `/api/payments/test` hook noted above. For a boring and
reliable smoke check after applying `deploy/envoy/`, port-forward Envoy:

```fish
kubectl port-forward -n resilience-lab svc/envoy-proxy 8080:80
curl http://localhost:8080/healthz
```

Access via Traefik only after you install Traefik CRDs/controller, create the TLS
Secret, and apply `deploy/traefik/ingressroute.yaml` (add
`resilience-lab.local` to `/etc/hosts` pointing at `$(minikube ip)` first):

```fish
curl -k https://resilience-lab.local/api/healthz
```

Or use `health-loop.sh` for a continuous stream of requests during chaos testing
after the Envoy service exists:

```fish
./scripts/health-loop.sh
```

Fires a request every 200ms to `localhost:8080/api/healthz` and prints the
HTTP status code — useful for watching the system recover in real time.

### Day-to-Day Helm Operations

```fish
# Upgrade after a Payments code change (rebuild resilience-lab-payments:local first)
make helm-up-dev
kubectl rollout restart deployment/resilience-lab-payments -n resilience-lab
kubectl rollout status deployment/resilience-lab-payments -n resilience-lab

# Upgrade after a local API code change (rebuild api:local first)
helm upgrade --install resilience-lab deploy/helm/ \
  --values deploy/helm/values-dev.yaml \
  --namespace resilience-lab \
  --set api.image.repository=api \
  --set api.image.tag=local
kubectl rollout restart deployment/resilience-lab-api -n resilience-lab
kubectl rollout status deployment/resilience-lab-api -n resilience-lab

# Rollback to previous revision
make rollback-1

# Rollback to specific revision N
make rollback-2

# Check release history
helm history resilience-lab -n resilience-lab

# Tear down the Helm release only
make helm-down

# Tear down the separately applied Envoy manifests too
kubectl delete -f deploy/envoy/
```

The rollout restart is intentional when you reuse the same local tag. Kubernetes
doesn't restart pods just because a same-named image was rebuilt inside minikube;
it needs a changed pod template or an explicit nudge. Computers, sadly, do not
smell fresh Docker layers.

### Observability Stack

Prometheus/Grafana and Loki are not in the main Helm chart — they're deployed
separately via kube-prometheus-stack and grafana/loki-stack. See
[docs/observability.md](observability.md) for the full setup walkthrough.

ServiceMonitor manifests at `deploy/prometheus/servicemonitor-*.yaml` connect
Prometheus to the API, Payments, and Envoy admin endpoints once the monitoring
stack is up and those manifests have been applied.

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
  fails with a missing binary. This is why it's in the image used for chaos
  runs and not just in a local shell.
- Port: `8001`

Security baseline applied in both:
- `RUN apt-get upgrade -y` — patches OS packages at build time
- `pip install --no-cache-dir` — no pip cache left in the layer
- `pip install --upgrade "wheel>=0.46.2"` — keeps the wheel package on a patched baseline
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

If GHCR packages are public, pull images without authentication:

```fish
docker pull ghcr.io/lotoos0/resilience-lab-api:latest
```

If the package visibility changes, authenticate first with `docker login ghcr.io`.

---

## CI/CD Pipeline

Two GitHub Actions workflows in `.github/workflows/`:

### CI (`ci.yml`) — every push and PR to `main`/`develop`

Runs 5 jobs. `lint`, `trivy-fs`, and `test` run in parallel. `integration-test`
and `build` both need `lint` and `test` to pass first:

```
lint ──────┬── integration-test
           │
test ──────┤
           └── build

trivy-fs (independent, runs in parallel)
```

| Job | What it does |
|-----|-------------|
| `lint` | `ruff check services/` |
| `trivy-fs` | Trivy filesystem scan (CRITICAL + HIGH), results to GitHub Security tab |
| `test` | Unit tests (`pytest -m "not integration"`) with postgres:16 + redis:7-alpine sidecar containers (mocked by tests), coverage → Codecov |
| `integration-test` | Spins up the Docker Compose stack, does a shallow health wait plus a 10s settle, runs `pytest -m integration`, tears down |
| `build` | Builds both images, runs Trivy image scan (exit-code 1 on CRITICAL/HIGH unfixed CVEs) |

**Note on CI service containers**: The test job spins up postgres:16 and
redis:7-alpine — but the unit tests mock both (Redis via `unittest.mock.Mock`,
PostgreSQL is unused entirely). The containers are there as groundwork for
future integration-level unit tests, not because anything currently requires
a live connection.

**Why integration tests are separate**: They need Docker Compose, which means
building images. Keeping them in a separate job lets `lint` and `test` fail fast
without waiting for Docker. The current CI wait loop checks for any `healthy`
container and then sleeps 10s; it is a pragmatic smoke gate, not a perfect
"all services are healthy" oracle. Tiny CI fortune cookie, basically.

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
Run `kubectl apply -f deploy/envoy/` before the Envoy-facing checks.

### Before Running Chaos

Make sure you're running with dev values:

```fish
make helm-up-dev
kubectl apply -f deploy/envoy/
```

### Latency Injection

Injects 300ms `tc netem` delay on all Payments pods:

```fish
./scripts/fault-inject.sh latency
```

This requires `NET_ADMIN` capability and `iproute2` in the container. If you
get "Operation not permitted", apply chaos overrides:

```fish
helm upgrade resilience-lab deploy/helm/ \
  -n resilience-lab \
  -f deploy/helm/values-dev.yaml \
  -f deploy/helm/values-chaos.yaml
kubectl rollout status deployment/resilience-lab-payments -n resilience-lab
```

`values-chaos.yaml` currently enables both `NET_ADMIN` and `runAsRoot: true` for
Payments because this cluster needed root for `tc netem` to behave. It is for
active experiments only; restore `values-dev.yaml` afterwards.

### FAIL_MODE and SLOW_MODE

Inject via env var — triggers an automatic rolling update (new pods come up with
the new env var, old ones terminate):

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
kubectl rollout status deployment/resilience-lab-payments -n resilience-lab
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
dedicated troubleshooting docs in `docs/runbooks/` and `docs/troubleshooting/`.
Short versions below.

### Pod stuck in `ImagePullBackOff`

Usually means the image tag in the Deployment does not exist where minikube is
looking. For the default dev setup, rebuild the Payments image inside minikube:

```fish
eval (minikube docker-env)
docker build -f services/payments/Dockerfile -t resilience-lab-payments:local .
make helm-up-dev
kubectl rollout restart deployment/resilience-lab-payments -n resilience-lab
kubectl rollout status deployment/resilience-lab-payments -n resilience-lab
```

If the API pod is the one failing, either make sure
`ghcr.io/lotoos0/resilience-lab-api:8b86f3d` is pullable, or build a local API
image and override both `api.image.repository` and `api.image.tag` as shown in
the first-time setup section.

### Helm upgrade fails with field ownership error

Happens when `kubectl` and Helm both manage the same field. Fix:

```fish
helm upgrade resilience-lab deploy/helm/ -n resilience-lab \
  -f deploy/helm/values-dev.yaml \
  --force-conflicts
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
