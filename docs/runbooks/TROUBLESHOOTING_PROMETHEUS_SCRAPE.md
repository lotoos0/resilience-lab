> This runbook was created based on a real incident observed in the Resilience Lab environment.

# Runbook: Prometheus cannot scrape API /metrics

**Status:** Active

**Owner:** Tomasz P. DevOps Team

**Last Updated:** 2026-01-08

**Severity:** P2 (Observability degradation)

## Description

Prometheus cannot scrape endpoint `/metrics` from API in namespace `resilience-lab`

## Impact / Blast Radius

- Affected: Prometheus metrics for API
- User-facing traffic impacted: NO
- Alerting / dashboards: OUT OF DATE
- Envoy metrics: OK

## Symptoms

- Prometheus `/targets` shows API as DOWN
- Errors:
  - `context deadline exceeded`
  - `HTTP 404 Not Found`
- API returns `500` on `/healthz`

## Root Cause

Middleware rate-limiting attempts to connect to Redis, but: 
- Redis does not have an **Ingress NetworkPolicy** 
- Connection timeout -> exception -> API responds with 500 
-`/metrics` cannot be returned

## Pre-flight Checks

```bash
kubectl -n resilience-lab get pods
kubectl -n resilience-lab logs <api-pod>
kubectl get netpol -n resilience-lab
```

## Resolution Steps

### Step 1: Check if the API actually works

```bash
kubectl exec -n resilience-lab <api-pod> -- python - << 'PY'
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8000/metrics", timeout=2)
PY
```

Error -> Go to Step 2

### Step 2: Check Redis/middleware logs

```bash
kubectl logs -n resilience-lab <api-pod> | grep redis
```

If logs contain:

`redis.exceptions.TimeoutError`

-> Likely Redis connectivity issue (NetworkPolicy / Service / DNS)

### Step 3: Check NetworkPolicy

```bash
kubectl describe netpol -n resilience-lab
```

No Ingress to Redis -> add NetworkPolicy allow-api-to-redis

### Step 4: Restart deployment

```bash
kubectl rollout restart deployment -n resilience-lab resilience-lab-api
```

## Verification

```bash
kubectl get pods -n resilience-lab
curl http://api.resilience-lab/metrics
```

**Success criteria:**

- [ ] API Ready 1/1
- [ ] `/metrics` -> 200
- [ ] Prometheus target -> UP

## Prevention / Long-term Fix

Long-term solution to prevent the problem in the future:

- [ ] Middleware: fail-open when Redis unavailable
- [ ] Bypass rate-limit for /metrics and /healthz
- [ ] Alert: Redis connection timeout
- [ ] Use specific image tags (not :dev/:latest) with imagePullPolicy=IfNotPresent

## Common Pitfalls / Gotchas

- Old pods in the namespace `default`
- `IfNotPresent` -> Old image
- Confusing ingress with egress in NetPol

## Additional Resources

- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Network Policies](../deploy/helm/templates/netpol-allow-essentials.yaml)
- [Prometheus Rules](../deploy/prometheus/rules.yaml)
- [Prometheus ServiceMonitor – API](../deploy/prometheus/servicemonitor-api.yaml)
- [Observability Overview](../docs/observability.md)

## Change History

| Date       | Author    | Changes                                            |
| ---------- | --------- | -------------------------------------------------- |
| 2026-01-08 | Tomasz P. | Created runbook after Prometheus /metrics incident |
| 2026-01-08 | Tomasz P. | Added Redis NetworkPolicy ingress verification     |
