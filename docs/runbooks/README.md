# Operational Runbooks

This directory contains operational runbooks created from real incidents
observed during the development of the Resilience Lab project.

## Available Runbooks

| Runbook | Severity | Status | Description |
|---------|----------|--------|-------------|
| [TEMPLATE](./TEMPLATE.md) | - | Active | Template for new runbooks |
| [Prometheus targets missing or firing after observability setup](./TROUBLESHOOTING_OBSERVABILITY_TARGETS.md) | P2 | Active | ServiceMonitor discovery, API /metrics 500, Envoy apply, HPA/Helm conflicts |
| [Prometheus cannot scrape API /metrics](./TROUBLESHOOTING_PROMETHEUS_SCRAPE.md) | P2 | Active | Redis connectivity + NetworkPolicy ingress issue |
| [Helm SSA field manager conflicts](./TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md) | P2 | Active | kubectl set image / apply steals field ownership from Helm; fix: --force-conflicts |
| [Minikube — ImagePullBackOff for local images](./TROUBLESHOOTING_MINIKUBE_IMAGES.md) | P2 | Active | Build images inside minikube via eval $(minikube docker-env) |

## Scope

Runbooks in this directory cover:
- **Observability failures** (Prometheus, metrics scraping)
- **NetworkPolicy and service connectivity** issues
- **Dependency failure scenarios** (Redis, PostgreSQL)
- **Kubernetes rollout and image lifecycle** problems

## Structure

Each runbook includes:
- **Description** - what we're solving
- **Impact/Blast Radius** - what's affected, user impact
- **Symptoms** - how to recognize the problem
- **Root Cause** - known underlying issue
- **Resolution Steps** - step-by-step procedure
- **Verification** - how to confirm it's fixed
- **Rollback** - what to do if something goes wrong
- **Prevention** - long-term solutions

## How to Create a New Runbook

1. Copy `TEMPLATE.md`
2. Name the file using convention: `<category>-<problem-name>.md`
   - Examples: `k8s-pod-crashloop.md`, `redis-connection-timeout.md`
3. Fill in all sections
4. Add entry to the table above
5. Test the procedure before marking as Active

## Categories

- **k8s-*** - Kubernetes issues
- **network-*** - Network, NetworkPolicy issues
- **monitoring-*** - Prometheus, Grafana
- **db-*** - Database issues
- **redis-*** - Redis issues
- **deploy-*** - Deployment issues

## Severity Levels

- **P0 (Critical)** - Production down, revenue impact
- **P1 (High)** - Severe problem, partial degradation
- **P2 (Medium)** - Non-critical, can wait
- **P3 (Low)** - Maintenance, optimizations

## Principles

1. **Keep it simple** - procedures must be clear and executable under pressure
2. **Test before commit** - every runbook should be tested
3. **Update after incident** - update runbook after each incident
4. **Version control** - maintain change history
