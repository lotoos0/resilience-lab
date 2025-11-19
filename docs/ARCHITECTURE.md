# 🏗️ Architecture Documentation

**Resilience Lab - System Architecture**

*Last updated: November 18, 2025*

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Service Architecture](#service-architecture)
- [Data Architecture](#data-architecture)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Architecture Decision Records](#architecture-decision-records)

---

## Overview

Resilience Lab is built as a **microservices architecture** designed for cloud-native deployment on Kubernetes. The system emphasizes:

- **Resilience**: Circuit breakers, retries, timeouts
- **Observability**: Metrics, logs, traces
- **Scalability**: Horizontal scaling, load balancing
- **Security**: Defense in depth, least privilege

### Key Principles

1. **Microservices First**: Small, focused services
2. **API-Driven**: RESTful APIs with OpenAPI specs
3. **Container Native**: Docker + Kubernetes
4. **12-Factor App**: Configuration via environment
5. **Event-Driven**: Async communication where appropriate

---

## System Architecture

### High-Level Architecture

```
                                    ┌──────────────┐
                                    │   Internet   │
                                    └──────┬───────┘
                                           │
                                    ┌──────▼───────┐
                                    │   Traefik    │
                                    │   (Ingress)  │
                                    └──────┬───────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                 ┌──────▼──────┐    ┌─────▼──────┐    ┌─────▼──────┐
                 │     API     │    │  Payments   │    │   Future   │
                 │   Gateway   │◄───┤   Service   │    │  Services  │
                 └──────┬──────┘    └─────┬───────┘    └────────────┘
                        │                  │
          ┌─────────────┼──────────────────┼──────────────┐
          │             │                  │              │
    ┌─────▼─────┐  ┌───▼────┐      ┌──────▼──────┐  ┌───▼────┐
    │PostgreSQL │  │ Redis  │      │ PostgreSQL  │  │ Redis  │
    │   (API)   │  │ (API)  │      │ (Payments)  │  │(Pmts)  │
    └───────────┘  └────────┘      └─────────────┘  └────────┘
```

### Component Layers

#### 1. **Ingress Layer**
- **Component**: Traefik (future)
- **Responsibilities**:
  - SSL/TLS termination
  - Request routing
  - Rate limiting
  - DDoS protection

#### 2. **Service Mesh Layer**
- **Component**: Envoy (future)
- **Responsibilities**:
  - Service-to-service communication
  - Circuit breaking
  - Retry logic
  - Observability (traces)

#### 3. **Application Layer**
- **Components**: API Gateway, Payments Service
- **Responsibilities**:
  - Business logic
  - Request/response handling
  - Authentication & authorization
  - Data validation

#### 4. **Data Layer**
- **Components**: PostgreSQL, Redis
- **Responsibilities**:
  - Data persistence
  - Caching
  - Session management

---

## Service Architecture

### API Gateway Service

**Purpose**: Main entry point for all client requests

**Technology Stack**:
- Language: Python 3.11
- Framework: FastAPI
- Server: Uvicorn

**Architecture Pattern**: Gateway Pattern

```
┌─────────────────────────────────────┐
│        API Gateway Service          │
│                                     │
│  ┌───────────────────────────────┐ │
│  │     Authentication Layer      │ │
│  │  (JWT, OAuth2 - future)       │ │
│  └───────────┬───────────────────┘ │
│              │                      │
│  ┌───────────▼───────────────────┐ │
│  │      Request Router           │ │
│  │  - Route to microservices     │ │
│  │  - Load balancing             │ │
│  └───────────┬───────────────────┘ │
│              │                      │
│  ┌───────────▼───────────────────┐ │
│  │    Resilience Layer           │ │
│  │  - Circuit breaker            │ │
│  │  - Retry logic                │ │
│  │  - Timeout handling           │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Key Features**:
- Health checks: `GET /healthz`
- OpenAPI docs: `GET /docs`
- Future: Authentication, rate limiting

**Configuration**:
- Port: 8000
- Database: PostgreSQL (shared)
- Cache: Redis (shared)

---

### Payments Service

**Purpose**: Handle payment processing and transaction management

**Technology Stack**:
- Language: Python 3.11
- Framework: FastAPI
- Server: Uvicorn

**Architecture Pattern**: Domain-Driven Design (DDD)

```
┌─────────────────────────────────────┐
│       Payments Service              │
│                                     │
│  ┌───────────────────────────────┐ │
│  │      API Layer                │ │
│  │  - REST endpoints             │ │
│  │  - Request validation         │ │
│  └───────────┬───────────────────┘ │
│              │                      │
│  ┌───────────▼───────────────────┐ │
│  │    Business Logic Layer       │ │
│  │  - Payment processing         │ │
│  │  - Validation rules           │ │
│  │  - Transaction management     │ │
│  └───────────┬───────────────────┘ │
│              │                      │
│  ┌───────────▼───────────────────┐ │
│  │      Data Access Layer        │ │
│  │  - Repository pattern         │ │
│  │  - Database operations        │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Key Features**:
- `POST /process` - Process payment
- `GET /payments/{id}` - Get payment details
- `GET /healthz` - Health check
- Validation: Amount > 0, Currency format

**Configuration**:
- Port: 8001
- Database: PostgreSQL (dedicated)
- In-memory store (temporary, will use PG in M1)

---

## Data Architecture

### Database Schema

#### Payments Database

```sql
-- Current: In-memory (Python dict)
-- Future (M1): PostgreSQL schema

CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_payments_tenant_id ON payments(tenant_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
```

### Caching Strategy

**Redis Usage**:
- Session management (future)
- Rate limiting counters (future)
- Temporary data storage
- Cache invalidation: TTL-based

**Cache Patterns**:
- Cache-aside (lazy loading)
- Write-through (for critical data)
- TTL: 5-60 minutes depending on data type

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────┐
│  1. Network Security                    │
│     - NetworkPolicy (K8s)               │
│     - TLS/SSL encryption                │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  2. Application Security                │
│     - Authentication (OAuth2/JWT)       │
│     - Input validation                  │
│     - Rate limiting                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  3. Container Security                  │
│     - Non-root user (appuser)           │
│     - Read-only filesystem (future)     │
│     - Security scanning                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  4. Data Security                       │
│     - Encryption at rest                │
│     - Encryption in transit             │
│     - Access controls                   │
└─────────────────────────────────────────┘
```

### Security Baseline (M0)

Current security measures:

1. **Container Security**:
   - Non-root user (`USER appuser`)
   - No cache in pip installs (`--no-cache-dir`)
   - Health checks (liveness/readiness)

2. **Input Validation**:
   - Pydantic models
   - Type checking
   - Business rule validation (amount > 0)

3. **Network Security** (future):
   - NetworkPolicy
   - Service mesh (mTLS)

---

## Deployment Architecture

### Local Development (Current)

```
┌──────────────────────────────────────┐
│        Docker Compose                │
│                                      │
│  ┌────────┐  ┌──────────┐           │
│  │  API   │  │ Payments │           │
│  └────┬───┘  └─────┬────┘           │
│       │            │                 │
│  ┌────▼────────────▼────┐           │
│  │    PostgreSQL         │           │
│  └───────────────────────┘           │
│  ┌───────────────────────┐           │
│  │       Redis           │           │
│  └───────────────────────┘           │
└──────────────────────────────────────┘
```

### Kubernetes (Future - M1)

```
┌──────────────────────────────────────────────┐
│           Kubernetes Cluster                 │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │         Ingress (Traefik)              │ │
│  └────────────────┬───────────────────────┘ │
│                   │                          │
│  ┌────────────────▼────────┐  ┌──────────┐  │
│  │  API Deployment         │  │ Payments │  │
│  │  - Replicas: 3          │  │Deployment│  │
│  │  - HPA: CPU > 70%       │  │- Reps: 2 │  │
│  │  - PDB: minAvailable=2  │  └──────────┘  │
│  └─────────────────────────┘                 │
│                                              │
│  ┌─────────────┐  ┌──────────────┐          │
│  │ PostgreSQL  │  │    Redis     │          │
│  │ StatefulSet │  │ StatefulSet  │          │
│  └─────────────┘  └──────────────┘          │
└──────────────────────────────────────────────┘
```

**Deployment Strategy**:
- Rolling updates (default)
- Canary deployments (future)
- Blue-green deployments (future)

---

## Architecture Decision Records

### ADR-001: Microservices Architecture

**Status**: Accepted

**Context**: Need scalable, maintainable system for resilience testing

**Decision**: Adopt microservices architecture with:
- Separate services per domain
- Independent deployment
- Dedicated databases (Database per Service pattern)

**Consequences**:
- ✅ Better scalability
- ✅ Independent deployment
- ✅ Technology flexibility
- ❌ Increased operational complexity
- ❌ Distributed system challenges

---

### ADR-002: FastAPI Framework

**Status**: Accepted

**Context**: Need modern, performant Python web framework

**Decision**: Use FastAPI for all services

**Rationale**:
- Automatic OpenAPI docs
- Built-in validation (Pydantic)
- Async support
- High performance
- Type hints

**Consequences**:
- ✅ Rapid development
- ✅ Built-in API docs
- ✅ Type safety
- ❌ Learning curve for async

---

### ADR-003: Docker Compose for Local Dev

**Status**: Accepted

**Context**: Need simple local development environment

**Decision**: Use Docker Compose for local development

**Rationale**:
- Easy setup
- Consistent environments
- Multi-service orchestration
- Good developer experience

**Consequences**:
- ✅ Simple setup (`make dev`)
- ✅ Environment parity
- ❌ Different from production (K8s)

---

### ADR-004: In-Memory Storage Initially

**Status**: Accepted (Temporary)

**Context**: M0 focus on infrastructure, not data persistence

**Decision**: Use in-memory storage in M0, migrate to PostgreSQL in M1

**Rationale**:
- Faster M0 completion
- Focus on infrastructure
- Easy migration path

**Consequences**:
- ✅ Rapid prototyping
- ✅ Simple testing
- ❌ Data loss on restart
- ❌ Migration work in M1

**Migration Plan**: M1 will add proper PostgreSQL schema and repositories

---

## Future Architecture

### Planned Enhancements (M1-M4)

**M1**:
- PostgreSQL persistence
- Helm charts
- Kubernetes deployment

**M2**:
- Service mesh (Envoy)
- Ingress controller (Traefik)
- NetworkPolicy

**M3**:
- Observability stack (Prometheus, Grafana, Loki)
- Circuit breakers
- Canary deployments

**M4**:
- Chaos engineering
- Multi-region deployment
- Advanced resilience patterns

---

## References

- [12-Factor App](https://12factor.net/)
- [Microservices Patterns](https://microservices.io/patterns/)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
