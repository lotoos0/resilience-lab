[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Milestone](https://img.shields.io/badge/Milestone-M0%20Bootstrap-blue)]()
[![Project Progress](https://img.shields.io/badge/Progress-25%25-yellow)]()
[![CI](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/lotoos0/resilience-lab/actions/workflows/ci.yml)

# 🔬 Resilience Lab

**A Kubernetes "resilience sandbox" for testing cloud-native failure patterns.**

> FastAPI + Envoy + Redis + Prometheus + Loki
> Deployable via Helm, observable via Grafana.

Resilience Lab is a hands-on platform for learning and testing cloud-native resilience patterns. It provides a complete microservices environment with observability, service mesh, and chaos engineering capabilities.

---

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
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

## 🏗️ Architecture

### System Overview

```
┌─────────────┐      ┌─────────────┐
│     API     │────▶│  Payments   │
│  (port 8000)│      │ (port 8001) │
└─────────────┘      └─────────────┘
      │                     │
      ├─────────────────────┤
      │                     │
      ▼                     ▼
┌─────────────┐      ┌─────────────┐
│ PostgreSQL  │      │    Redis    │
│  (port 5432)│      │  (port 6379)│
└─────────────┘      └─────────────┘
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

#### Infrastructure

- **PostgreSQL 16**: Primary database
- **Redis 7**: Cache and session store

### Design Patterns

- **Microservices**: Independently deployable services
- **Health Checks**: Built-in health monitoring
- **12-Factor App**: Environment-based configuration
- **Security**: Non-root containers, health checks

---

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

### 🔜 M1 - Core & CI/CD (Nov 17-25, 2025)

- [ ] Helm charts for Kubernetes deployment
- [ ] Full CI/CD with `--atomic` deployments
- [ ] Enhanced security (runAsNonRoot, readOnlyRootFS)
- [ ] Database migrations
- [ ] API authentication

### 🔜 M2 - Networking (Nov 26-30, 2025)

- [ ] Traefik ingress controller
- [ ] Envoy service mesh
- [ ] HPA (Horizontal Pod Autoscaler)
- [ ] PDB (Pod Disruption Budget)
- [ ] NetworkPolicy

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

_Last updated: November 21, 2025_
