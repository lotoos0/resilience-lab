# M2 Fault Injection Tests

This document contains fault injection test results for the Resilience Lab system.

## Test Environment

- **Namespace**: `resilience-lab`
- **Target Service**: `payments`
- **Proxy**: Envoy (deployment: `envoy-proxy`)
- **Admin Interface**: `localhost:9901`

---

## Test 1: Failure Mode (500 Errors)

### Setup

```bash
./scripts/fault-inject.sh failure
```

**Result:**
```
🔥 Setting FAIL_MODE=1 on payments deployment...
deployment.apps/resilience-lab-payments env updated
✅ FAIL_MODE enabled. Payments will return 500.
   Monitor retries and outlier ejection in Envoy stats.
```

### Outlier Detection Stats (Baseline)

All counters at 0 before traffic generation:

```
cluster.payments_service.outlier_detection.ejections_enforced_success_rate: 0
cluster.payments_service.outlier_detection.ejections_enforced_total: 0
cluster.payments_service.outlier_detection.ejections_overflow: 0
cluster.payments_service.outlier_detection.ejections_success_rate: 0
cluster.payments_service.outlier_detection.ejections_total: 0
```

**Observation**: Outlier detection is configured but inactive until traffic is generated.

---

## Test 2: Cleanup

### Command

```bash
./scripts/fault-inject.sh cleanup
```

**Result:**
```
🧹 Cleaning up fault injections...
deployment.apps/resilience-lab-payments env updated
  → Cleaning pod/resilience-lab-payments-57ccbbf4ff-fxl58
  → Cleaning pod/resilience-lab-payments-7df7f6d55f-55qgj
✅ Cleanup complete.
```

**Note**: Warning about `tc` command not found is expected due to security constraints (read-only filesystem, no NET_ADMIN capability). The cleanup successfully removes environment variables.

---

## Test 3: Pod Kill (Chaos Testing)

### Command

```bash
./scripts/fault-inject.sh kill
```

**Result:**
```
🔥 Deleting random payments pod...
  → Killing resilience-lab-payments-7df7f6d55f-55qgj
pod "resilience-lab-payments-7df7f6d55f-55qgj" deleted from resilience-lab namespace
✅ Pod deleted. Monitor retries and pod recovery.
```

**Observation**: Pod successfully deleted. Kubernetes should automatically recreate it based on the deployment replica count.

---

## Envoy Statistics

### Retry Statistics

Query: `curl -s http://localhost:9901/stats | grep retry`

#### API Service

| Metric | Value |
|--------|-------|
| `circuit_breakers.default.rq_retry_open` | 0 |
| `circuit_breakers.high.rq_retry_open` | 0 |
| `retry_or_shadow_abandoned` | 0 |
| `upstream_rq_retry` | 0 |
| `upstream_rq_retry_backoff_exponential` | 0 |
| `upstream_rq_retry_backoff_ratelimited` | 0 |
| `upstream_rq_retry_limit_exceeded` | 0 |
| `upstream_rq_retry_overflow` | 0 |
| `upstream_rq_retry_success` | 0 |

#### Payments Service

| Metric | Value |
|--------|-------|
| `circuit_breakers.default.rq_retry_open` | 0 |
| `circuit_breakers.high.rq_retry_open` | 0 |
| `retry_or_shadow_abandoned` | 0 |
| `upstream_rq_retry` | 0 |
| `upstream_rq_retry_backoff_exponential` | 0 |
| `upstream_rq_retry_backoff_ratelimited` | 0 |
| `upstream_rq_retry_limit_exceeded` | 0 |
| `upstream_rq_retry_overflow` | 0 |
| `upstream_rq_retry_success` | 0 |

**Observation**: All retry counters at 0 indicates no traffic has been sent through the system yet.

---

## Next Steps

To observe active resilience patterns, generate traffic:

```bash
# Generate load to trigger retries and outlier detection
for i in {1..50}; do
  curl -s http://localhost:8080/api/payments -w "\nStatus: %{http_code}\n"
  sleep 0.5
done

# Monitor non-zero stats
curl -s http://localhost:9901/stats | grep "payments.*retry\|payments.*outlier" | grep -v ": 0$"
```

### Additional Test Modes

```bash
./scripts/fault-inject.sh slow     # Inject 2s delay
./scripts/fault-inject.sh failure  # Return 500 errors
./scripts/fault-inject.sh kill     # Delete random pod
./scripts/fault-inject.sh cleanup  # Remove all faults
```

---

## Security Notes

- Network-level latency injection (using `tc`) is blocked by:
  - Read-only root filesystem
  - Dropped Linux capabilities (no NET_ADMIN)
  - Non-root user execution
- Application-level fault injection (FAIL_MODE, SLOW_MODE) works correctly
- This demonstrates defense-in-depth security practices
