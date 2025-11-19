# 🚀 Deployment Guide

**Resilience Lab - Deployment Documentation**

*Last updated: November 18, 2025*

---

## Table of Contents

- [Overview](#overview)
- [Local Deployment](#local-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Production Considerations](#production-considerations)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

---

## Overview

Resilience Lab supports multiple deployment targets:

| Environment | Status | Purpose |
|------------|--------|---------|
| **Local (Docker Compose)** | ✅ Available (M0) | Development, testing |
| **Kubernetes (Helm)** | 🚧 Planned (M1) | Production, staging |
| **Cloud (Managed K8s)** | 🔮 Future (M2+) | Production at scale |

---

## Local Deployment

### Quick Start (Development)

**Prerequisites**:
- Docker 24+
- Docker Compose v2+
- Make

**Steps**:

1. **Clone and setup**:
   ```bash
   git clone https://github.com/lotoos0/resilience-lab.git
   cd resilience-lab
   ```

2. **Start services**:
   ```bash
   make dev
   ```

3. **Verify deployment**:
   ```bash
   make ps
   curl http://localhost:8000/healthz
   curl http://localhost:8001/healthz
   ```

### Configuration

#### Environment Variables

Create `.env` file (optional):

```bash
# Database
POSTGRES_USER=resilience
POSTGRES_PASSWORD=resilience
POSTGRES_DB=resilience_db

# Redis
REDIS_URL=redis://redis:6379

# Services
API_PORT=8000
PAYMENTS_PORT=8001

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

#### Custom docker-compose Override

Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  api:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    ports:
      - "8000:8000"

  payments:
    environment:
      - DEBUG=true
    ports:
      - "8001:8001"
```

### Port Mapping

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| API | 8000 | 8000 | HTTP |
| Payments | 8001 | 8001 | HTTP |
| PostgreSQL | 5432 | 5432 | TCP |
| Redis | 6379 | 6379 | TCP |

### Data Persistence

**Volumes**:
- `pgdata`: PostgreSQL data
- `redisdata`: Redis data

**Location**: Docker volumes (managed by Docker)

**Backup**:
```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U resilience resilience_db > backup.sql

# Backup Redis
docker compose exec redis redis-cli SAVE
docker compose cp redis:/data/dump.rdb ./redis-backup.rdb
```

**Restore**:
```bash
# Restore PostgreSQL
cat backup.sql | docker compose exec -T postgres psql -U resilience -d resilience_db

# Restore Redis
docker compose cp ./redis-backup.rdb redis:/data/dump.rdb
docker compose restart redis
```

### Cleanup

```bash
# Stop services (keep data)
make down

# Stop and remove volumes (DELETE DATA)
docker compose down -v

# Clean everything
make clean
```

---

## Kubernetes Deployment

> **Status**: Planned for M1 (Nov 17-25, 2025)

### Prerequisites

- Kubernetes cluster (1.25+)
- Helm 3+
- kubectl configured
- Container registry access (GHCR)

### Architecture

```
┌─────────────────────────────────────────┐
│         Kubernetes Cluster              │
│                                         │
│  ┌────────────────────────────────┐    │
│  │  Ingress (Traefik)             │    │
│  │  resilience-lab.example.com    │    │
│  └────────────┬───────────────────┘    │
│               │                         │
│  ┌────────────▼──────┐  ┌──────────┐   │
│  │ API Service       │  │ Payments │   │
│  │ - Deployment      │  │ Service  │   │
│  │ - Replicas: 3     │  │ - Dep    │   │
│  │ - HPA enabled     │  │ - Rep: 2 │   │
│  │ - PDB: min=2      │  └──────────┘   │
│  └───────────────────┘                 │
│                                         │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ PostgreSQL   │  │    Redis      │   │
│  │ StatefulSet  │  │  StatefulSet  │   │
│  │ - PVC: 10Gi  │  │  - PVC: 5Gi   │   │
│  └──────────────┘  └───────────────┘   │
└─────────────────────────────────────────┘
```

### Helm Deployment (M1)

**Coming in M1**. Expected structure:

```bash
# Add Helm repository
helm repo add resilience-lab https://lotoos0.github.io/resilience-lab-helm

# Install
helm install resilience-lab resilience-lab/resilience-lab \
  --namespace resilience-lab \
  --create-namespace \
  --values values-production.yaml

# Upgrade
helm upgrade resilience-lab resilience-lab/resilience-lab \
  --namespace resilience-lab \
  --values values-production.yaml

# Rollback
helm rollback resilience-lab 1 --namespace resilience-lab
```

### Kubernetes Resources

#### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: resilience-lab
  labels:
    name: resilience-lab
    environment: production
```

#### API Deployment (Example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: resilience-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: ghcr.io/lotoos0/resilience-lab-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### HPA (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: resilience-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### PDB (Pod Disruption Budget)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
  namespace: resilience-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: resilience-lab-ingress
  namespace: resilience-lab
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  ingressClassName: traefik
  tls:
  - hosts:
    - resilience-lab.example.com
    secretName: resilience-lab-tls
  rules:
  - host: resilience-lab.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 8000
      - path: /payments
        pathType: Prefix
        backend:
          service:
            name: payments
            port:
              number: 8001
```

---

## Production Considerations

### Security

#### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: resilience-lab
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: payments
    ports:
    - protocol: TCP
      port: 8001
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

#### Secrets Management

```bash
# Create secrets
kubectl create secret generic db-credentials \
  --from-literal=url='postgresql://user:pass@postgres:5432/db' \
  --namespace resilience-lab

# Or use Sealed Secrets / External Secrets Operator
```

### Resource Limits

**Recommended limits per service**:

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| API | 250m | 500m | 256Mi | 512Mi |
| Payments | 250m | 500m | 256Mi | 512Mi |
| PostgreSQL | 500m | 1000m | 512Mi | 1Gi |
| Redis | 100m | 200m | 128Mi | 256Mi |

### Health Checks

**Liveness Probe**: Restart if unhealthy
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

**Readiness Probe**: Remove from load balancer if unhealthy
```yaml
readinessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 2
```

### Scaling Strategy

**Horizontal Scaling**:
- HPA based on CPU/Memory
- Target: 70% CPU utilization
- Min replicas: 2
- Max replicas: 10

**Vertical Scaling**:
- VPA (Vertical Pod Autoscaler) - future
- Resource optimization based on metrics

---

## Monitoring & Observability

> Detailed monitoring coming in M3

### Health Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `GET /healthz` | `{"status":"healthy"}` |
| Payments | `GET /healthz` | `{"status":"healthy"}` |

### Metrics (Future - M3)

**Prometheus metrics**:
- HTTP request duration
- Request count by status code
- Database connection pool stats
- Cache hit/miss ratio

**Access**: `http://service:8000/metrics`

### Logging (Future - M3)

**Structured logging with Loki**:
```json
{
  "timestamp": "2025-11-18T10:00:00Z",
  "level": "INFO",
  "service": "payments",
  "message": "Payment processed",
  "payment_id": "uuid",
  "amount": 100.0,
  "duration_ms": 45
}
```

### Tracing (Future - M3)

**OpenTelemetry + Jaeger**:
- Distributed tracing
- Request flow visualization
- Performance bottleneck identification

---

## Backup & Recovery

### Database Backup

**Automated backups** (Future - M1):

```bash
# CronJob for daily backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16
            command:
            - sh
            - -c
            - pg_dump -U resilience resilience_db | gzip > /backup/backup-$(date +%Y%m%d).sql.gz
```

### Disaster Recovery

**RTO (Recovery Time Objective)**: < 1 hour
**RPO (Recovery Point Objective)**: < 24 hours

**Recovery Steps**:
1. Deploy from Helm chart
2. Restore database from backup
3. Verify services health
4. Run smoke tests
5. Route traffic

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -n resilience-lab

# Describe pod
kubectl describe pod <pod-name> -n resilience-lab

# Check logs
kubectl logs <pod-name> -n resilience-lab

# Check events
kubectl get events -n resilience-lab --sort-by='.lastTimestamp'
```

### Service Unavailable

```bash
# Check service
kubectl get svc -n resilience-lab

# Check endpoints
kubectl get endpoints -n resilience-lab

# Test connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# wget -O- http://api:8000/healthz
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl logs postgres-0 -n resilience-lab

# Test connection
kubectl exec -it postgres-0 -n resilience-lab -- psql -U resilience -d resilience_db

# Check secrets
kubectl get secret db-credentials -n resilience-lab -o yaml
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n resilience-lab

# Check HPA status
kubectl get hpa -n resilience-lab

# Check metrics
kubectl describe hpa api-hpa -n resilience-lab
```

---

## CI/CD Integration

### GitHub Actions Deployment

**Workflow** (`.github/workflows/deploy.yml`):

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          echo "${{ secrets.KUBECONFIG }}" > kubeconfig
          export KUBECONFIG=kubeconfig

      - name: Deploy with Helm
        run: |
          helm upgrade --install resilience-lab ./deploy/helm/resilience-lab \
            --namespace resilience-lab \
            --set image.tag=${{ github.sha }} \
            --atomic \
            --timeout 5m
```

---

## Next Steps

1. **M1**: Implement Helm charts
2. **M2**: Add Traefik + Envoy
3. **M3**: Implement full observability stack
4. **M4**: Production-ready deployment

For more information:
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEVELOPMENT.md](./DEVELOPMENT.md)
- [Helm Charts](../deploy/helm/) (coming in M1)
