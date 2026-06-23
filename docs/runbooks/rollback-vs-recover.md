# Rollback vs Recover Runbook

**Namespace:** `resilience-lab`
**Applies to:** All Deployments in the resilience-lab cluster

---

## Purpose

This runbook answers one question during a partial outage:

> **Should I wait for Kubernetes to recover automatically, or should I manually rollback the deployment?**

---

## Decision Flow

```
Pod fails or is killed
         │
         ▼
Is a new pod being scheduled?
         │
    ┌────┴────┐
   YES        NO
    │          │
    ▼          ▼
Does it     Check describe pod /
reach       events for reason
Ready?      (OOMKilled, ErrImagePull, etc.)
    │
 ┌──┴──┐
YES    NO
 │      │
 ▼      ▼
RECOVER  Is this the current
         version that started failing?
              │
         ┌────┴────┐
        YES        NO
         │          │
         ▼          ▼
      ROLLBACK   Investigate
                 (infra issue,
                  config, secret)
```

---

## Recover: Wait for Automatic Recovery

**Use recovery when:**

- Only one pod failed or was deleted
- The Deployment's ReplicaSet creates a replacement pod
- The new pod reaches `1/1 Running` within 60 seconds
- No repeated `CrashLoopBackOff` appears on the new pod
- Traffic returns to `2xx` after the replacement starts

**Verify recovery:**

```bash
kubectl get pods -n resilience-lab -w
kubectl get events -n resilience-lab --sort-by=.lastTimestamp | tail -20
kubectl logs -n resilience-lab deploy/resilience-lab-payments --tail=50
```

**Expected timeline for payments service:**

| Time | Expected state |
|------|---------------|
| 0s   | Pod deleted / killed |
| ~2s  | New pod scheduled and image pulled (already on node) |
| ~15s | New pod `1/1 Running` |
| ~30s | Envoy outlier detection re-includes pod (if it was ejected) |

---

## Rollback: Manual Intervention

**Use rollback when:**

- New pods fail to become `Ready` (CrashLoopBackOff, OOMKilled, startup probe failures)
- Errors continue after the replacement pod starts
- `5xx` rate keeps increasing after recovery
- The last deployment introduced the regression (check `kubectl rollout history`)
- Multiple pods fail in sequence (not an isolated pod kill)

**Check rollout history:**

```bash
kubectl rollout history deployment/resilience-lab-payments -n resilience-lab
kubectl rollout history deployment/resilience-lab-payments -n resilience-lab --revision=<N>
```

**Rollback command:**

```bash
kubectl rollout undo deployment/resilience-lab-payments -n resilience-lab
```

**Verify rollback:**

```bash
kubectl rollout status deployment/resilience-lab-payments -n resilience-lab
kubectl get pods -n resilience-lab | grep payments
```

**Rollback via Helm** (preferred if deployed via Helm):

```bash
helm rollback resilience-lab <REVISION> -n resilience-lab
```

Find the revision:

```bash
helm history resilience-lab -n resilience-lab
```

---

## HPA and PDB Considerations

### HPA

HPA scales based on CPU/memory. If metrics-server is unavailable, HPA will not scale — the Deployment holds its current replica count. A single pod kill without HPA scaling means there is a brief capacity reduction until the replacement is ready.

If HPA is working and the replacement pod comes up healthy, HPA will continue normal operation. No manual intervention needed.

### PDB

`resilience-lab-payments-pdb` requires MIN AVAILABLE=1.

- If only 1 replica is running, ALLOWED DISRUPTIONS=0 — voluntary evictions (e.g. `kubectl drain`) are blocked.
- Direct `kubectl delete pod` bypasses PDB and proceeds regardless.
- After recovery, PDB resets automatically when the replacement pod becomes Ready.

If a rolling update is stuck because PDB blocks eviction, check:

```bash
kubectl describe pdb resilience-lab-payments-pdb -n resilience-lab
```

To unblock temporarily (use with caution):

```bash
kubectl patch pdb resilience-lab-payments-pdb -n resilience-lab \
  --type='json' -p='[{"op":"replace","path":"/spec/minAvailable","value":0}]'
```

Restore after the update completes:

```bash
kubectl patch pdb resilience-lab-payments-pdb -n resilience-lab \
  --type='json' -p='[{"op":"replace","path":"/spec/minAvailable","value":1}]'
```

---

## Envoy Behavior During Pod Kill

Envoy outlier detection is configured:

```yaml
consecutive_5xx: 3
base_ejection_time: 30s
max_ejection_percent: 50
```

With a single payments host:
- Envoy cannot eject it (50% of 1 = 0 hosts ejectable)
- Requests during pod restart window will fail at the connection level
- Retry policy (num_retries: 2, per_try_timeout: 200ms) will retry but has no alternate host

With 2+ payments replicas (HPA scaled up):
- Envoy can eject the killed pod's connection attempts
- Remaining replicas absorb traffic
- Outlier detection re-includes the new pod after `base_ejection_time`

**Recommendation:** For production, keep HPA minReplicas ≥ 2 to allow Envoy outlier detection to work effectively and eliminate user-visible outage during pod kill.

---

## Quick Reference

```bash
# Check current pod state
kubectl get pods -n resilience-lab

# Watch recovery in real time
kubectl get pods -n resilience-lab -w

# Check events (rehydration timeline)
kubectl get events -n resilience-lab --sort-by=.lastTimestamp | tail -30

# Check HPA
kubectl get hpa -n resilience-lab

# Check PDB
kubectl get pdb -n resilience-lab

# Rollback payments
kubectl rollout undo deployment/resilience-lab-payments -n resilience-lab

# Rollback via Helm
helm history resilience-lab -n resilience-lab
helm rollback resilience-lab <REVISION> -n resilience-lab
```

---

## Related

- [Chaos Pod Kill Test](chaos-pod-kill.md)
- [Chaos Latency Injection](chaos-latency-injection.md)
- [M3 Resilience Patterns](../M3_RESILIENCE_PATTERNS.md)
