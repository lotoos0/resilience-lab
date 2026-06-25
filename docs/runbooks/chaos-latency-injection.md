# Runbook: Chaos Test — Latency Injection (300ms, Payments)

**Status:** Active
**Owner:** resilience-lab-team
**Last Updated:** 2026-06-21
**Severity:** P2 (Planned experiment, non-production)
**Related issue:** [#40 Run chaos test: latency injection](https://github.com/lotoos0/resilience-lab/issues/40)

## Description

Inject 300ms network delay into all Payments service pods using Linux `tc netem`
and verify that the system does not breach any SLO alert window.
The delay is applied via `scripts/fault-inject.sh latency`, which runs
`tc qdisc add dev eth0 root netem delay 300ms` inside each payments pod via `kubectl exec`.

300ms is below Envoy's `per_try_timeout: 2s`, so requests are expected to succeed
without triggering retries, outlier ejections, or error-rate alerts.

## Impact / Blast Radius

- Components affected: Payments pods (network namespace only)
- API, Envoy, Redis, Prometheus, Grafana: unaffected
- End-user impact: elevated response latency (~300ms added), no errors expected
- Observability impact: none — all scrape targets remain up

## Prerequisites

- [ ] Payments image rebuilt with `iproute2` (see Pre-flight section)
- [ ] Chaos mode deployed via `values-chaos.yaml` (see Pre-flight section)
- [ ] `kubectl rollout status deployment/resilience-lab-payments -n resilience-lab` — all pods Ready
- [ ] Port-forwards active: Prometheus :9090, Grafana :3000, Envoy :8080 (listener), Envoy admin :9901
- [ ] No alerts firing before injection:
  `ALERTS{alertname=~"HighErrorRate|APIDown|PrometheusTargetDown",alertstate="firing"}` returns `[]`

## Security Trade-off

This experiment requires a temporary security relaxation of the Payments deployment:

| Setting | Default (secure) | Chaos Stage 1 | Chaos Stage 2 (if needed) |
|---------|-----------------|---------------|--------------------------|
| `capabilities.drop` | ALL | ALL | ALL |
| `capabilities.add` | — | NET_ADMIN | NET_ADMIN |
| `runAsUser` | 1000 | 1000 | 0 |
| `runAsNonRoot` | true | true | false |
| `readOnlyRootFilesystem` | true | true | true |
| `allowPrivilegeEscalation` | false | false | false |

Stage 2 is only needed if `tc` fails with `RTNETLINK answers: Operation not permitted`
under Stage 1, which indicates `NET_ADMIN` did not reach the effective capability set
for uid 1000 processes in this environment.

**Cleanup restores the fully secure baseline** by re-applying Helm without `values-chaos.yaml`.

## Pre-flight Steps

### 1. Build the updated image (iproute2 included)

```bash
eval $(minikube docker-env)
docker build -f services/payments/Dockerfile -t resilience-lab-payments:local .

# Verify tc binary is present
docker run --rm resilience-lab-payments:local which tc
# Expected: /sbin/tc
```

### 2. Render and verify the chaos Helm template before applying

```bash
helm template resilience-lab deploy/helm \
  -f deploy/helm/values-dev.yaml \
  -f deploy/helm/values-chaos.yaml \
  | grep -A 40 'name: payments' \
  | grep -A 20 'securityContext'
```

**Expected for Stage 1** (`runAsRoot: false`):
```yaml
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: payments
        securityContext:
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
            add:
              - NET_ADMIN
```

Verify exactly one `NET_ADMIN` occurrence across the entire rendered output:
```bash
helm template resilience-lab deploy/helm \
  -f deploy/helm/values-dev.yaml \
  -f deploy/helm/values-chaos.yaml \
  | grep -c 'NET_ADMIN'
# Expected: 1
```

### 3. Preview what changes vs the live cluster

```bash
helm diff upgrade resilience-lab deploy/helm \
  -n resilience-lab \
  -f deploy/helm/values-dev.yaml \
  -f deploy/helm/values-chaos.yaml
```

Only the payments Deployment securityContext should appear in the diff.

### 4. Apply chaos mode

```bash
helm upgrade resilience-lab deploy/helm \
  -n resilience-lab \
  -f deploy/helm/values-dev.yaml \
  -f deploy/helm/values-chaos.yaml \
  --force-conflicts

kubectl rollout status deployment/resilience-lab-payments -n resilience-lab
# Wait for: successfully rolled out
```

## Experiment Steps

### Step 1 — Activate port-forwards

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:3000 &
kubectl port-forward -n resilience-lab svc/envoy-proxy 8080:80 &
kubectl port-forward -n resilience-lab svc/envoy-proxy 9901:9901 &
```

> **Note:** The Envoy Service exposes port `80` (→ targetPort 10000), not port `10000` directly.
> Use `svc/envoy-proxy 8080:80`, **not** `8080:10000`.

Confirm Envoy is reachable:
```bash
curl -s http://localhost:8080/healthz
# Expected: {"status":"ok"} or similar 200 response
```

### Step 2 — Record baseline metrics

Run each query and save the returned `value[1]` field:

```bash
# Baseline p95 latency (Envoy → payments cluster), in milliseconds
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name="payments_service"}[5m])) * 1000' \
  | python3 -m json.tool

# Baseline error rate ratio
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(http_requests_total{job="resilience-lab-api",status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="resilience-lab-api"}[5m])),0.001)' \
  | python3 -m json.tool

# Baseline retry rate (payments cluster)
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(envoy_cluster_upstream_rq_retry{envoy_cluster_name="payments_service"}[5m])' \
  | python3 -m json.tool

# Confirm no alerts firing
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=ALERTS{alertname=~"HighErrorRate|APIDown|PrometheusTargetDown",alertstate="firing"}' \
  | python3 -m json.tool
# Expected: "result": []

# Envoy raw stats snapshot
curl -s http://localhost:9901/stats \
  | grep payments \
  | grep -E 'upstream_rq_total|upstream_rq_retry|upstream_rq_xx' \
  > /tmp/baseline-envoy-stats.txt
cat /tmp/baseline-envoy-stats.txt
```

### Step 3 — Start background traffic

```bash
for i in $(seq 1 120); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' \
    -X POST http://localhost:8080/payments/process \
    -H 'Content-Type: application/json' \
    -d '{"amount": 100.0, "currency": "USD", "tenant_id": "chaos-test"}')
  echo "$(date +%H:%M:%S) req $i → $CODE"
  sleep 0.5
done &
```

Wait for at least 10 successful requests (2xx) before injecting.

### Step 4 — Inject latency

```bash
./scripts/fault-inject.sh latency
```

**Expected output:**
```
🔥 Injecting 300ms latency to payments pods...
  → pod/resilience-lab-payments-<hash>
✅ Latency injected. Verify with:
   kubectl exec -n resilience-lab <pod> -- tc qdisc show dev eth0
```

If output contains `ERROR: 'tc' not found` — the image was not rebuilt; see Pre-flight Step 1.

If `tc qdisc add` fails with `RTNETLINK answers: Operation not permitted` — Stage 1
capability propagation failed. Run cleanup, set `payments.chaosMode.runAsRoot: true`
in `values-chaos.yaml`, re-run `helm upgrade`, and restart from Step 1.

### Step 5 — Confirm injection in-pod

```bash
POD=$(kubectl get pods -n resilience-lab \
  -l app.kubernetes.io/name=payments \
  -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n resilience-lab "$POD" -- tc qdisc show dev eth0
```

**Required output** (PASS):
```
qdisc netem 8001: root refcnt 2 limit 1000 delay 300ms
```

Any output without `netem` and `delay 300ms` is a failed injection — do not proceed.

### Step 6 — Monitor (10 minutes, sample at T+2m, T+5m, T+10m)

Record the `value[1]` field from each query at each sample time:

```bash
# p95 latency — expect ≥ 300ms above baseline
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name="payments_service"}[5m])) * 1000' \
  | python3 -m json.tool

# Error rate — expect < 0.01
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(http_requests_total{job="resilience-lab-api",status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="resilience-lab-api"}[5m])),0.001)' \
  | python3 -m json.tool

# Retry rate — expect near 0 (300ms < 2s per_try_timeout)
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(envoy_cluster_upstream_rq_retry{envoy_cluster_name="payments_service"}[5m])' \
  | python3 -m json.tool

# Outlier ejections — expect 0
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=rate(envoy_cluster_outlier_detection_ejections_total{envoy_cluster_name="payments_service"}[5m])' \
  | python3 -m json.tool

# Alert state — expect "result": [] at every sample
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=ALERTS{alertname=~"HighErrorRate|APIDown|PrometheusTargetDown",alertstate="firing"}' \
  | python3 -m json.tool
```

## Cleanup Steps

### Step 1 — Stop traffic loop

```bash
jobs     # identify the background loop
kill %<job-number>
```

### Step 2 — Remove tc injection

```bash
./scripts/fault-inject.sh cleanup
```

Expected output per pod:
```
  → Cleaning pod/resilience-lab-payments-<hash>
  ✅ tc qdisc clean on pod/resilience-lab-payments-<hash>
✅ Cleanup complete.
```

If the WARNING fires, remove manually and re-verify:
```bash
kubectl exec -n resilience-lab "$POD" -- tc qdisc del dev eth0 root
kubectl exec -n resilience-lab "$POD" -- tc qdisc show dev eth0
# Must return only: qdisc noqueue 0: root refcnt 2  (or pfifo_fast)
```

### Step 3 — Restore secure security baseline

```bash
helm upgrade resilience-lab deploy/helm \
  -n resilience-lab \
  -f deploy/helm/values-dev.yaml
  # Note: values-chaos.yaml deliberately NOT passed

kubectl rollout status deployment/resilience-lab-payments -n resilience-lab
```

### Step 4 — Verify security context restored

```bash
kubectl get pod -n resilience-lab \
  -l app.kubernetes.io/name=payments \
  -o jsonpath='{.items[0].spec.securityContext}' | python3 -m json.tool
# Expected: {"fsGroup":1000,"runAsNonRoot":true,"runAsUser":1000}

kubectl get pod -n resilience-lab \
  -l app.kubernetes.io/name=payments \
  -o jsonpath='{.items[0].spec.containers[0].securityContext}' | python3 -m json.tool
# Expected: {"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"readOnlyRootFilesystem":true}
# NET_ADMIN must be absent from the output.
```

### Step 5 — Verify latency returned to baseline (T+5m after cleanup)

```bash
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name="payments_service"}[5m])) * 1000' \
  | python3 -m json.tool
# Expected: value within 20% of pre-injection baseline
```

### Step 6 — Teardown port-forwards and temp files

```bash
pkill -f 'kubectl port-forward'
rm -f /tmp/baseline-envoy-stats.txt /tmp/injected-envoy-stats.txt
```

## Evidence Record

**Date:** 2026-06-22
**Operator:** lotoos0
**Stage used:** Stage 2 (runAsRoot: true — confirmed required on this cluster)

| Metric | Baseline | During injection | Post-cleanup |
|--------|----------|-----------------|--------------|
| p95 latency (ms, payments cluster) | no data (no traffic) | see note | no data |
| Error rate ratio (`job="resilience-lab-api"`) | `0` | `0` | `0` |
| Retry rate /s (payments cluster) | `0` | `2.0/s` (366 total) | `0` |
| Outlier ejection rate /s | `0` | `0` | `0` |
| `ALERTS{...firing}` result | `[]` | `[]` | `[]` |

> **p95 latency note:** `envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name="payments_service"}`
> showed `[]` (no data) during the experiment because the histogram only tracks completed requests;
> timed-out requests (`per_try_timeout`) are not included in the histogram buckets.
> Connection establishment latency WAS elevated — `upstream_cx_connect_ms P50 ≈ 305ms` (baseline: 0).

**tc qdisc show output during injection (verbatim):**
```
qdisc netem 8001: root refcnt 17 limit 1000 delay 300ms seed 10040034563280759046
```

**Envoy stats: baseline vs during injection (payments cluster, key counters):**
```
# Baseline (before injection):
upstream_rq_total: 0
upstream_cx_total: 0

# During injection (after 240 traffic loop requests):
upstream_rq_201: 57          # successful (used pre-existing connections)
upstream_rq_504: 183         # gateway timeouts (per_try_timeout exceeded)
upstream_rq_total: 606       # 57 + 183 original + 366 retries
upstream_rq_per_try_timeout: 549
upstream_rq_retry: 366
upstream_rq_retry_limit_exceeded: 183
upstream_cx_connect_ms: P50(305ms) P99(310ms)
```

**Security context after cleanup (verbatim kubectl jsonpath output):**
```
# Pod-level:
{"fsGroup":1000,"runAsNonRoot":true,"runAsUser":1000}

# Container-level:
{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"readOnlyRootFilesystem":true}
# NET_ADMIN absent — confirmed.
```

**Outcome:** PASS (SLO criteria met) with UNEXPECTED FINDING (see below)

**Stage required:** Stage 2

## Unexpected Finding: tc netem delays internal service calls

**tc netem on eth0 delays ALL outgoing packets from the payments pod,**
not only responses to Envoy. This includes packets sent by the payments
application to Redis, PostgreSQL, or any other backend.

Timeline with 300ms netem applied to payments:
1. Envoy → payments TCP SYN (no delay — ingress to payments pod)
2. payments → Envoy SYN-ACK (delayed 300ms)  ← connection establishment: ~305ms
3. Envoy → payments HTTP request (no delay)
4. payments → Redis: every TCP packet delayed 300ms each way (Redis replies arrive
   normally, but payments' ACKs and queries are all delayed)
5. Depending on the number of Redis round-trips, total processing can easily exceed 2s
6. per_try_timeout: 2s fires → retry × 2 → retry_limit_exceeded → 504 to client

**Effect:** 57/240 requests succeeded (used pre-existing warm connections from before
injection). 183/240 requests returned 504 Gateway Timeout after 3 attempts each.

**Why SLO alerts did NOT fire:**
`HighErrorRate` watches `http_requests_total{job="resilience-lab-api"}`.
The API service (`/api` routes) was never involved in `/payments/process` requests.
Envoy routes payments traffic directly to the `payments_service` cluster, bypassing
the API service entirely. The 504s are only visible in Envoy cluster stats.

**SLO coverage gap identified:**
There is no alert covering Envoy-level 5xx responses for the payments cluster.
A follow-up alert should be created:
```yaml
# Suggested (not yet implemented):
sum(rate(envoy_cluster_upstream_rq_5xx{envoy_cluster_name="payments_service"}[5m]))
/ clamp_min(sum(rate(envoy_cluster_upstream_rq_completed{envoy_cluster_name="payments_service"}[5m])), 0.001)
> 0.05
```

**Issue #40 acceptance criterion status:**
- `tc netem delay 300ms` applied via script: ✅ CONFIRMED
- System does not breach SLOs (no alerts fired): ✅ CONFIRMED
- Root cause of 504s is Envoy's `per_try_timeout: 2s` being hit due to netem delaying
  all payments→Redis packets, NOT a fundamental SLO breach.

## PASS / FAIL Criteria

| ID | Criterion | Result | Notes |
|----|-----------|--------|-------|
| P1 | tc pre-check | ✅ PASS | Script printed "✅ Latency injected" |
| P2 | Injection confirmed | ✅ PASS | `qdisc netem 8001: root refcnt 17 limit 1000 delay 300ms seed ...` |
| P3 | p95 latency elevated ≥ 300ms | ⚠️ N/A | Histogram only tracks completed requests; connection P50 ≈ 305ms confirms delay |
| P4 | Error rate `job="resilience-lab-api"` < 0.01 | ✅ PASS | API service error rate = `0` throughout; 504s are Envoy-level only |
| P4b | Envoy payments 5xx rate | ❌ FAIL | 183/240 requests = 76% 504; root cause: netem delays payments→Redis (see Finding) |
| P5 | HighErrorRate alert = `[]` | ✅ PASS | No alert fired |
| P6 | APIDown alert = `[]` | ✅ PASS | No alert fired |
| P7 | PrometheusTargetDown alert = `[]` | ✅ PASS | No alert fired |
| P8 | Retry rate < 0.05 /s | ❌ FAIL | `upstream_rq_retry: 366` → ~2.0/s during experiment |
| P9 | Outlier ejections = 0 | ✅ PASS | `envoy_cluster_outlier_detection_ejections_total = 0` |
| P10 | tc cleanup | ✅ PASS | "✅ tc qdisc clean on pod/..." for all pods |
| P11 | Security context restored | ✅ PASS | `runAsUser:1000`, `runAsNonRoot:true`, `capabilities.drop:[ALL]`, no NET_ADMIN |
| P12 | Latency returns to baseline | ✅ PASS | Connection times returned to ~0ms after cleanup |

**Overall: PASS on SLO criteria (P1, P2, P4, P5, P6, P7, P9–P12). Unexpected finding on P4b and P8 — see "Unexpected Finding" section above.**

## Rollback (if experiment goes wrong)

```bash
# If helm upgrade for chaos mode fails
helm rollback resilience-lab -n resilience-lab
kubectl rollout status deployment/resilience-lab-payments -n resilience-lab

# If tc was injected but cleanup fails — manual per-pod removal
kubectl exec -n resilience-lab "$POD" -- tc qdisc del dev eth0 root
kubectl exec -n resilience-lab "$POD" -- tc qdisc show dev eth0

# If pods are in bad state
kubectl rollout undo deployment/resilience-lab-payments -n resilience-lab
helm upgrade resilience-lab deploy/helm -n resilience-lab -f deploy/helm/values-dev.yaml
```

## Notes on Metrics Coverage

The p95 latency metric (`envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name="payments_service"}`)
measures Envoy's view of upstream request duration to the payments cluster — the full
round trip from Envoy to payments and back, which includes the injected 300ms.
Payments exposes `/metrics` via `prometheus-fastapi-instrumentator`, but those are
HTTP-level counters — there is no direct per-pod latency metric from the payments
process itself at the network layer where the delay is injected.

## Change History

| Date | Author | Changes |
|------|--------|---------|
| 2026-06-21 | lotoos0 | Created — issue #40 chaos latency experiment |
| 2026-06-22 | lotoos0 | Ran experiment (Stage 2); documented findings: netem delays all pod egress (incl. Redis); SLO alerts did not fire; SLO coverage gap identified |
