[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Milestone](https://img.shields.io/badge/Milestone-M2%20Networking%20%26%20Health-blue)]()
[![Project Progress](https://img.shields.io/badge/Progress-60%25-yellow)]()
[![CI](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml)

# 🔬 Resilience Lab

**A Kubernetes “resilience sandbox” for testing cloud-native failure patterns before they hit production.**

> FastAPI + PostgreSQL + Redis today
> Helm, GitHub Actions, security baseline, CI pipeline already in place
> Envoy + Traefik networking layer with resilience policies (retry, timeout, circuit breaker)
> Prometheus, Grafana, Loki and chaos tooling – planned in upcoming milestones.

Resilience Lab is a hands-on platform for learning and practicing cloud-native resilience patterns.  
It provides a realistic microservices environment (API + Payments + PostgreSQL + Redis) with:

- local Docker Compose setup for fast development,
- Helm-based Kubernetes deployment for staging/“lab” clusters,
- CI/CD pipeline (lint → unit → integration → build → publish to GHCR),
- security baseline (non-root, healthchecks, Trivy scans).

Current milestone (M2) provides production-grade networking layer with Traefik ingress controller and Envoy front-proxy featuring resilience policies (retry, timeout, circuit breaker).
Upcoming milestones extend this lab with observability (Prometheus, Grafana, Loki) and chaos experiments.

---

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Kubernetes Deployment with Helm](#-kubernetes-deployment-with-helm)
- [Architecture](#-architecture)
- [M2 Progress: Networking & Health](#-m2-progress-networking--health--envoy-policies-complete)
- [Development](#-development)
- [Testing](#-testing)
- [CI/CD](#-cicd)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:

### Required

- **Docker** 24+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** v2+ (comes with Docker Desktop)
- **Python** 3.11+ ([Install Python](https://www.python.org/downloads/))
- **Make** (usually pre-installed on Linux/macOS)

### Optional (for development)

- **Git** 2.40+
- **kubectl** (for Kubernetes deployment)
- **Helm** 3+ (for chart deployment)
- **k3d/kind/minikube** (for local Kubernetes cluster)

### Platform Support

- ✅ Linux (tested on Ubuntu 22.04+, Arch Linux)
- ✅ macOS 12+
- ✅ Windows 10/11 (via WSL2)

---

## 🚀 Quick Start

Get the project running in under 5 minutes:

### 1. Clone the repository

```bash
git clone https://github.com/lotoos0/resilience-lab.git
cd resilience-lab
```

### 2. Start all services

```bash
make dev
```

This will start:

- **API Service** (port 8000): Main gateway service
- **Payments Service** (port 8001): Payment processing service
- **PostgreSQL** (port 5432): Database
- **Redis** (port 6379): Cache

### 3. Verify services are running

```bash
# Check all services status
make ps

# Health checks
curl http://localhost:8000/healthz
curl http://localhost:8001/healthz
```

Expected output:

```json
{"status":"healthy","service":"api"}
{"status":"healthy","service":"payments"}
```

### 4. Test the payment flow

```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "currency": "USD"}'
```

Expected output:

```json
{
  "payment_id": "uuid-here",
  "status": "completed",
  "amount": 100.0,
  "currency": "USD"
}
```

### 5. Stop services

```bash
make down
```

---

## ☸️ Kubernetes Deployment with Helm

Deploy Resilience Lab to Kubernetes using Helm charts for production-grade orchestration.

### Prerequisites

Before deploying to Kubernetes, ensure you have:

**Required:**

- **kubectl** 1.28+ ([Install kubectl](https://kubernetes.io/docs/tasks/tools/))
- **Helm** 3.10+ ([Install Helm](https://helm.sh/docs/intro/install/))
- **Kubernetes cluster** (one of the following):
  - **k3d** 5.0+ - Lightweight local cluster ([Install k3d](https://k3d.io/#installation))
  - **minikube** 1.32+ - Local Kubernetes ([Install minikube](https://minikube.sigs.k8s.io/docs/start/))
  - **kind** 0.20+ - Kubernetes in Docker ([Install kind](https://kind.sigs.k8s.io/docs/user/quick-start/))
  - **Docker Desktop** - Built-in Kubernetes
  - **Cloud provider** - GKE, EKS, AKS, etc.

**Verify installation:**

```bash
kubectl version --client
helm version
kubectl cluster-info
```

### Installation Instructions

#### 1. Create local Kubernetes cluster (optional)

If you don't have a cluster, create one with k3d:

```bash
# Create a new k3d cluster
k3d cluster create resilience-cluster \
  --api-port 6550 \
  --servers 1 \
  --agents 2 \
  --port "8080:80@loadbalancer"

# Verify cluster is running
kubectl get nodes
```

Alternative with minikube:

```bash
# Start minikube
minikube start --cpus 4 --memory 8192

# Verify cluster
kubectl get nodes
```

#### 2. Build Helm dependencies

Build the chart dependencies (API and Payments subcharts):

```bash
make helm-deps
```

Or manually:

```bash
helm dependency build deploy/helm/
```

#### 3. Deploy to Kubernetes

**Development environment:**

```bash
# Install with development values
make helm-up-dev
```

This command:

- Creates namespace `resilience-lab`
- Deploys API service (1 replica)
- Deploys Payments service (1 replica)
- Deploys PostgreSQL database
- Deploys Redis cache

**Production environment:**

```bash
# Install with production values
helm upgrade --install resilience-lab deploy/helm/ \
  --namespace resilience-lab \
  --create-namespace \
  --wait \
  --timeout 5m
```

**Custom configuration:**

```bash
# Install with custom values
helm upgrade --install resilience-lab deploy/helm/ \
  --namespace resilience-lab \
  --create-namespace \
  --set api.replicaCount=3 \
  --set payments.replicaCount=3 \
  --set global.imageRegistry=ghcr.io \
  --wait
```

#### 4. Verify deployment

```bash
# Check all pods are running
kubectl get pods -n resilience-lab

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# resilience-lab-api-xxxxx                1/1     Running   0          2m
# resilience-lab-payments-xxxxx           1/1     Running   0          2m
# resilience-lab-postgresql-0             1/1     Running   0          2m
# resilience-lab-redis-master-0           1/1     Running   0          2m

# Check services
kubectl get svc -n resilience-lab

# View logs
kubectl logs -n resilience-lab -l app.kubernetes.io/name=api
kubectl logs -n resilience-lab -l app.kubernetes.io/name=payments
```

### Testing Instructions

#### 1. Port-forward to access services

```bash
# Forward API service to localhost:8000
kubectl port-forward -n resilience-lab svc/resilience-lab-api 8000:8000

# In another terminal, forward Payments service
kubectl port-forward -n resilience-lab svc/resilience-lab-payments 8001:8001
```

#### 2. Test health endpoints

```bash
# Test API service
curl http://localhost:8000/healthz

# Expected output:
# {"status":"healthy","service":"api"}

# Test Payments service
curl http://localhost:8001/healthz

# Expected output:
# {"status":"healthy","service":"payments"}
```

#### 3. Test payment processing

```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "currency": "USD"}'

# Expected output:
# {
#   "payment_id": "uuid-here",
#   "status": "completed",
#   "amount": 100.0,
#   "currency": "USD"
# }
```

#### 4. Run Helm tests

```bash
# Run Helm test suite
make helm-test

# Or manually:
helm test resilience-lab --namespace resilience-lab
```

### Monitoring and Troubleshooting

#### View pod status and logs

```bash
# Get pod status
kubectl get pods -n resilience-lab -w

# Describe pod for details
kubectl describe pod -n resilience-lab <pod-name>

# View logs
kubectl logs -n resilience-lab <pod-name> --follow

# View logs for all API pods
kubectl logs -n resilience-lab -l app.kubernetes.io/name=api --all-containers --follow
```

#### Common issues

**Pods stuck in Pending:**

```bash
# Check events
kubectl get events -n resilience-lab --sort-by='.lastTimestamp'

# Check resource availability
kubectl describe nodes
```

**ImagePullBackOff errors:**

```bash
# Check image pull status
kubectl describe pod -n resilience-lab <pod-name>

# Verify images exist
docker pull ghcr.io/lotoos0/resilience-lab-api:latest
docker pull ghcr.io/lotoos0/resilience-lab-payments:latest
```

### Upgrading the Deployment

```bash
# Upgrade with new values
helm upgrade resilience-lab deploy/helm/ \
  --namespace resilience-lab \
  --values deploy/helm/values.yaml \
  --wait

# Rollback to previous version
make helm-rollback 1

# Or manually:
helm rollback resilience-lab 1 --namespace resilience-lab
```

### Uninstallation

```bash
# Uninstall Helm release
make helm-down

# Or manually:
helm uninstall resilience-lab --namespace resilience-lab

# Delete namespace (optional)
kubectl delete namespace resilience-lab

# Delete k3d cluster (if using k3d)
k3d cluster delete resilience-cluster
```

### Advanced Configuration

#### Custom values file

Create a custom values file (`my-values.yaml`):

```yaml
api:
  replicaCount: 3
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"

payments:
  replicaCount: 3
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"

postgresql:
  primary:
    persistence:
      size: 5Gi

redis:
  master:
    persistence:
      size: 2Gi
```

Deploy with custom values:

```bash
helm upgrade --install resilience-lab deploy/helm/ \
  --namespace resilience-lab \
  --create-namespace \
  --values my-values.yaml \
  --wait
```

#### Helm chart structure

```
deploy/helm/
├── Chart.yaml              # Main chart metadata
├── Chart.lock              # Dependency lock file
├── values.yaml             # Default values
├── values-dev.yaml         # Development overrides
├── templates/              # Kubernetes manifests
└── charts/                 # Subcharts
    ├── api/                # API service chart
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    └── payments/           # Payments service chart
        ├── Chart.yaml
        ├── values.yaml
        └── templates/
```

---

## 🏗️ Architecture

### System Overview

```
        User/Browser
             │
             ▼
     ┌──────────────┐
     │   Traefik    │ ← HTTPS ingress controller
     │(IngressRoute)│   (port 80/443)
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │    Envoy     │ ← Front-proxy (routing, health checks)
     │  (proxy)     │   (port 10000)
     └──────┬───────┘
            │
       ┌────┴────┐
       │         │
       ▼         ▼
┌───────────┐  ┌───────────┐
│    API    │  │  Payments │
│(port 8000)│  │(port 8001)│
└─────┬─────┘  └────┬──────┘
      │             │
      └──────┬──────┘
             │
      ┌──────┴───────┐
      │              │
      ▼              ▼
┌───────────┐  ┌───────────┐
│PostgreSQL │  │  Redis    │
│(port 5432)│  │(port 6379)│
└───────────┘  └───────────┘
```

### Services

#### API Service (`services/api/`)

- **Purpose**: Main API gateway
- **Tech Stack**: FastAPI, Python 3.11
- **Responsibilities**:
  - Request routing
  - Authentication (future)
  - Rate limiting (future)
- **Endpoints**:
  - `GET /healthz` - Health check
  - More endpoints coming in M1

#### Payments Service (`services/payments/`)

- **Purpose**: Payment processing
- **Tech Stack**: FastAPI, Python 3.11
- **Responsibilities**:
  - Payment processing
  - Transaction management
- **Endpoints**:
  - `GET /healthz` - Health check
  - `POST /process` - Process payment
  - `GET /payments/{id}` - Get payment by ID

#### Networking Layer

##### Traefik (`deploy/traefik/`)

- **Purpose**: HTTPS ingress controller
- **Tech Stack**: Traefik v2+
- **Responsibilities**:
  - TLS termination (self-signed certificate)
  - Ingress routing via IngressRoute CRD
  - Entry point for external traffic
- **Configuration**:
  - `ingressroute.yaml` - HTTP and HTTPS routing rules
  - Routes traffic to Envoy front-proxy

##### Envoy (`deploy/envoy/`)

- **Purpose**: Front-proxy and traffic management with resilience policies
- **Tech Stack**: Envoy Proxy v1.28+
- **Responsibilities**:
  - Service routing (API, Payments)
  - Health checking backend services
  - Load balancing (Round Robin)
  - **Retry policy** (2 retries, 2s per-try timeout)
  - **Timeout policy** (10s request, 60s idle)
  - **Outlier detection** (circuit breaker, 3 consecutive 5xx → 30s ejection)
  - Admin interface for observability
- **Configuration**:
  - `envoy-config.yaml` - ConfigMap with routing rules and resilience policies
  - `envoy-deployment.yaml` - 2 replicas with health probes
  - `envoy-service.yaml` - ClusterIP service
- **Endpoints**:
  - Port 10000: Main proxy endpoint
  - Port 9901: Admin interface

#### Infrastructure

- **PostgreSQL 16**: Primary database
- **Redis 7**: Cache and session store

### Design Patterns

- **Microservices**: Independently deployable services
- **Health Checks**: Built-in health monitoring
- **Circuit Breaker**: Automatic outlier detection and ejection
- **Retry Pattern**: Automatic retries on transient failures
- **Timeout Pattern**: Request and idle timeouts
- **12-Factor App**: Environment-based configuration
- **Security**: Non-root containers, health checks

---

## 📊 M2 Progress: Networking & Health (✅ Envoy Policies Complete)

The M2 milestone focuses on building a production-grade networking layer with resilience policies.

### Traefik Ingress

- ✅ **Traefik IngressRoute** with self-signed TLS certificate
- ✅ **HTTPS routing**: `resilience-lab.local` → Envoy proxy
- ✅ **TLS termination** at ingress level

### Envoy Front-Proxy

- ✅ **Service routing** to API and Payments services
- ✅ **Health checks** (5s interval, 2/2 healthy/unhealthy threshold)
- ✅ **Retry policy**: 2 retries on 5xx/reset/connect-failure with 2s per-try timeout
- ✅ **Timeout policy**: 10s request timeout, 60s idle timeout
- ✅ **Outlier detection** (circuit breaker): 3 consecutive 5xx → 30s ejection
- ✅ **Headless services**: Envoy sees individual pod IPs for accurate outlier detection

### Architecture Flow

```
User → Traefik (HTTPS/TLS) → Envoy (resilience policies) → API/Payments Services
```

### Resilience Features Verified

**Retry Policy:**

- Automatic retries on transient failures (5xx, connection errors)
- Per-try timeout prevents hanging requests
- Retry host predicate avoids retrying same failing host

**Timeout Policy:**

- Request-level timeouts prevent resource exhaustion
- Idle timeouts for long-lived connections
- Global and per-route timeout configuration

**Outlier Detection (Circuit Breaker):**

- Detects failing hosts via consecutive 5xx errors
- Automatic ejection of unhealthy endpoints (30s base ejection time)
- Max 50% of hosts can be ejected to maintain availability
- Verified with pod failure simulation: `ejections_enforced_total: 1`

### Testing Resilience

```bash
# Test retry policy on pod failure
kubectl delete pod -l app.kubernetes.io/name=api -n resilience-lab
curl -H "Host: resilience-lab.local" http://localhost:8080/api/healthz
# Should succeed due to retry policy + healthy pods

# Check Envoy outlier ejection stats
kubectl port-forward -n resilience-lab svc/envoy-proxy 9901:9901
curl http://localhost:9901/stats | grep outlier

# View clusters and health status
curl http://localhost:9901/clusters | grep -E "health_flags|ejected"
```

### Fault Injection Testing

Test resilience features using built-in fault injection scripts:

```bash
# Inject 500 errors (test outlier ejection)
./scripts/fault-inject.sh failure

# Inject 2s delay (test timeout policy)
./scripts/fault-inject.sh slow

# Kill random pod (test retry policy and auto-recovery)
./scripts/fault-inject.sh kill

# Cleanup all injections
./scripts/fault-inject.sh cleanup
```

**Monitor Envoy statistics during tests:**

```bash
# Port-forward Envoy admin interface
kubectl port-forward -n resilience-lab svc/envoy-proxy 9901:9901

# Check outlier detection, retries, and timeouts
curl http://localhost:9901/stats | grep -E 'outlier|retry|timeout'
```

**Expected results:**
- **FAIL_MODE**: Triggers outlier detection after 3 consecutive 5xx errors
- **SLOW_MODE**: Triggers per-try timeouts (2s) and retries
- **Pod Kill**: Kubernetes auto-recovers pod within ~30s, retries ensure no downtime

See `docs/M2_FAULT_TESTS.md` for detailed test results and analysis.

### High Availability & Security

- ✅ **HPA (HorizontalPodAutoscaler)**: Auto-scaling 2-5 replicas (CPU 70%, Memory 80%)
- ✅ **PDB (PodDisruptionBudget)**: minAvailable: 1 for zero-downtime updates
- ✅ **NetworkPolicy**: Default-deny with allow-list for Envoy → Service

### Key Implementation Details

**Headless Services:**
Services use `clusterIP: None` to enable Envoy endpoint discovery. This allows Envoy to see individual pod IPs instead of a single ClusterIP, which is required for outlier detection to function correctly.

**Load Balancing:**
Round-robin load balancing across healthy endpoints with automatic failover to healthy hosts when outlier detection ejects failing ones.

---

## 🌍 Environments & Real-World Usage

Resilience Lab is not “another app”.  
It is a **platform** you can run your microservices on – before they reach real players/users.

A typical real-world setup looks like this:

```text
               GitHub (game/backend repo)
                         │
                         ▼
                 GitHub Actions CI/CD
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
      🧪 LAB / STAGING         🎮 PRODUCTION
  (Resilience Lab cluster)   (players' backend)
```

- **LAB / STAGING (Resilience Lab)**
  - Helm deploys the microservices into a Kubernetes cluster used only by developers.
  - Here you run:
    - integration tests,
    - resilience experiments (timeouts, retries, HPA, PDB, NetworkPolicies),
    - later: rate-limiting, circuit breakers, canary releases, chaos experiments.

  - No real players / customers hit this environment.

- **PRODUCTION**
  - Uses the **same Docker images, Helm charts and CI/CD patterns**,
    but deployed to a separate cluster (or EC2-based environment).
  - This is where the _official_ backend for the game/app runs.

### Example: game backend

You can plug a game backend into this lab, e.g.:

- `game-store` microservice (item shop),
- `inventory` microservice,
- `profile` microservice.

Flow:

1. Developer pushes changes to `game-backend` repo.
2. CI builds Docker images and deploys them to the **LAB cluster** using the patterns from this project.
3. If tests and resilience checks pass, the same images + Helm values are promoted to the **PRODUCTION cluster** where real players connect.

In other words:

> **Resilience Lab defines how you build, deploy and test microservices safely,
> production defines where your players/users actually connect.**

## 💻 Development

### Setup Development Environment

#### Option 1: Using virtual environment (recommended)

```bash
# Install Python dependencies
make install

# Activate virtual environment (optional)
source venv/bin/activate

# Start services
make dev
```

#### Option 2: Without virtual environment

```bash
# Use Docker-based testing
make test-docker
```

### Available Make Targets

Run `make help` to see all available commands:

```bash
# Setup
make install          # Install dev dependencies in venv
make install-full     # Install all dependencies (requires postgresql-libs)

# Development
make dev              # Start all services
make run              # Alias for 'dev'
make down             # Stop all services
make restart          # Restart all services
make ps               # Show services status
make logs             # Show all logs
make logs-api         # Show API logs only
make logs-payments    # Show Payments logs only

# Building
make build            # Build Docker images

# Testing & Quality
make test             # Run all tests
make test-unit        # Run unit tests only
make test-integration # Run integration tests (requires: make dev)
make test-docker      # Run tests in Docker container
make lint             # Run code linters

# Cleanup
make clean            # Clean Docker resources
make clean-venv       # Remove virtual environment
```

### Project Structure

```
resilience-lab/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   └── main.py
│   └── payments/
│       ├── Dockerfile
│       └── main.py
├── tests/
│   ├── test_sanity.py          # Basic sanity tests
│   └── test_integration.py     # Integration tests
├── docs/                       # Documentation
├── docker-compose.yml          # Local development setup
├── Makefile                    # Development commands
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Dev-only dependencies
└── pytest.ini                  # Pytest configuration
```

### Coding Standards

- **Python**: PEP 8 (enforced by `ruff`)
- **Linting**: Run `make lint` before committing
- **Testing**: Maintain >80% code coverage
- **Commit Messages**: Use conventional commits format
  - `[DAYxx] type: description`
  - Types: `feat`, `fix`, `docs`, `ci`, `test`, `refactor`

### Adding a New Service

1. Create service directory: `services/your-service/`
2. Add `Dockerfile` with security baseline
3. Add `main.py` with FastAPI app
4. Update `docker-compose.yml`
5. Add health check endpoint
6. Add tests in `tests/`
7. Update this README

---

## 🧪 Testing

### Test Structure

The project uses `pytest` with separate test categories:

- **Unit Tests**: Fast, no external dependencies
- **Integration Tests**: Require running services

### Running Tests

#### All tests (requires running services)

```bash
make dev          # Start services first
make test         # Run all tests
```

#### Unit tests only (no services needed)

```bash
make test-unit
```

#### Integration tests (requires services)

```bash
make dev                # Start services
make test-integration   # Run integration tests
```

#### Docker-based testing

```bash
make test-docker   # No local setup needed
```

### Test Coverage

```bash
# Install coverage tools
pip install pytest-cov

# Run with coverage report
pytest --cov=services --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Writing Tests

**Unit Test Example:**

```python
# tests/test_sanity.py
def test_sanity():
    """Basic sanity check."""
    assert 1 + 1 == 2
```

**Integration Test Example:**

```python
# tests/test_integration.py
import pytest
import requests

pytestmark = pytest.mark.integration

def test_payment_endpoint():
    """Test payment processing."""
    response = requests.post(
        "http://localhost:8001/process",
        json={"amount": 100, "currency": "USD"}
    )
    assert response.status_code == 201
```

---

## 🔄 CI/CD

### Pipeline Overview

The project uses **GitHub Actions** for continuous integration and deployment.

```
Trigger (push/PR)
    ↓
┌─────────┐
│  Lint   │ ← Ruff code quality checks
└────┬────┘
     │
     ├──→ ┌─────────┐
     │    │  Test   │ ← Unit tests (pytest)
     │    └────┬────┘
     │         │
     ├─────────┴──→ ┌───────────────────┐
     │              │ Integration Test  │ ← Full stack tests
     │              └────────┬──────────┘
     │                       │
     └───────────────────────┴──→ ┌─────────┐
                                  │  Build  │ ← Docker images
                                  └────┬────┘
                                       │
                    (main/develop) ───→│
                                       ↓
                              ┌─────────────────┐
                              │ Build and Push  │ ← GHCR
                              └─────────────────┘
```

### Pipeline Jobs

#### 1. **Lint** (`lint`)

- **Purpose**: Code quality checks
- **Tools**: `ruff`
- **Runs on**: All pushes and PRs
- **Duration**: ~30s

#### 2. **Test** (`test`)

- **Purpose**: Unit tests
- **Services**: PostgreSQL, Redis
- **Tests**: Unit tests only (`pytest -m "not integration"`)
- **Duration**: ~1min

#### 3. **Integration Test** (`integration-test`)

- **Purpose**: End-to-end testing
- **Setup**: Full docker-compose stack
- **Tests**: Integration tests (`pytest -m integration`)
- **Duration**: ~2min

#### 4. **Build** (`build`)

- **Purpose**: Verify Docker builds
- **Images**: API, Payments
- **Duration**: ~2min

#### 5. **Build and Push** (`build-and-push`)

- **Purpose**: Publish to GHCR
- **Trigger**: Only on `main` or `develop`
- **Registry**: GitHub Container Registry
- **Tags**:
  - `latest`
  - `{commit-sha}`

### Workflow Configuration

File: `.github/workflows/ci.yml`

**Triggers:**

- Push to: `main`, `develop`, `test/**`, `feature/**`
- Pull requests to: `main`, `develop`

### Container Registry

Images are published to **GitHub Container Registry** (GHCR):

```bash
# Pull images
docker pull ghcr.io/lotoos0/resilience-lab-api:latest
docker pull ghcr.io/lotoos0/resilience-lab-payments:latest

# Run from registry
docker run -p 8000:8000 ghcr.io/lotoos0/resilience-lab-api:latest
```

### Status Badges

Current build status: [![CI](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml)

---

## 🗺️ Roadmap

### ✅ M0 - Bootstrap (Oct 28-31, Nov 17-19, 2025) - **COMPLETED**

- [x] API + Payments services
- [x] Docker Compose setup
- [x] Comprehensive CI/CD pipeline (lint, test, integration, build, publish)
- [x] Unit + Integration tests with pytest
- [x] Security baseline (non-root, healthchecks)
- [x] GHCR integration with automated publishing
- [x] Comprehensive documentation (6 docs, 3000+ lines)
  - [x] README, CONTRIBUTING, CODE_OF_CONDUCT
  - [x] Architecture, Development, Deployment guides
  - [x] M0 Retrospective

### ✅ M1 - Core & CI/CD (Nov 17-26, 2025) - **COMPLETED**

- [x] Helm charts for Kubernetes deployment
- [x] Production-grade SecurityContext (runAsNonRoot, readOnlyRootFS, capabilities)
- [x] Health probes (startup, liveness, readiness)
- [x] Trivy security scanning (filesystem + Docker images)
- [x] CVE remediation (CVE-2024-47874, CVE-2025-62727)
- [x] Makefile targets for Helm operations
- [x] Kubernetes documentation (300+ lines)
- [x] M1 Retrospective

### 🚧 M2 - Networking & Health (Nov 26-30, 2025) - **IN PROGRESS**

- [x] Traefik ingress controller (IngressRoute with TLS)
- [x] Envoy front-proxy (routing, health checks, load balancing)
- [x] Envoy resilience policies (retries, timeouts, outlier ejection)
- [x] Headless services for Envoy endpoint discovery
- [x] HPA (Horizontal Pod Autoscaler)
- [x] PDB (Pod Disruption Budget)
- [x] NetworkPolicy (allow-list security)

### 🔜 M3 - Resilience + Observability (Dec 1-15, 2025)

- [ ] Rate limiting (Envoy)
- [ ] Circuit breaker patterns
- [ ] Bulkhead isolation
- [ ] Canary deployments
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Loki log aggregation

### 🔜 M4 - Release (Dec 16-31, 2025)

- [ ] Chaos engineering (Chaos Mesh)
- [ ] Backup/restore procedures
- [ ] Performance testing
- [ ] Documentation site
- [ ] v1.0.0 release

---

## 📚 Additional Resources

### Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System architecture, design patterns, ADRs
- **[Development Guide](docs/DEVELOPMENT.md)** - Setup, coding standards, debugging
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Local and Kubernetes deployment
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute, PR process, commit format
- **[Code of Conduct](CODE_OF_CONDUCT.md)** - Community guidelines
- **[Retrospectives](docs/RETROSPECTIVES.md)** - Milestone retrospectives and lessons learned

### API Documentation

Available when services are running:

- **API Service**: http://localhost:8000/docs
- **Payments Service**: http://localhost:8001/docs

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Run linting (`make lint`)
6. Commit your changes (`git commit -m '[DAYxx] feat: add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## 🧾 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/lotoos0/resilience-lab/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lotoos0/resilience-lab/discussions)
- **Email**: andii4444@gmail.com

---

**Built with ❤️ for cloud-native resilience engineering**

_Last updated: November 29, 2025_
