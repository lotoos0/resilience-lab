# Runbook: [Problem/Operation Title]

**Status:** Draft | Active | Deprecated
**Owner:** [Name / Team]
**Last Updated:** YYYY-MM-DD
**Severity:** P0 (Critical) | P1 (High) | P2 (Medium) | P3 (Low)

## Description

Brief description of the problem, incident, or maintenance operation.

## Impact / Blast Radius

- Which components are affected: (API / Envoy / Metrics / Traffic)
- Does the problem affect end users: YES / NO
- Is this observability-only issue: YES / NO

## Symptoms

How to recognize that this problem is occurring:

- Symptom 1
- Symptom 2
- Example errors in logs
- Metrics/alerts that are triggered

## Root Cause

Known root cause of the problem (if known).

## Pre-flight Checks

**Prerequisites:**

- [ ] Access to Kubernetes cluster
- [ ] Access to Prometheus/Grafana
- [ ] Access to logs (kubectl logs)

**Problem Verification:**

```bash
# Commands to confirm the problem exists
kubectl get pods -n resilience-lab
kubectl logs -n resilience-lab <pod-name>
```

## Resolution Steps

### Step 1: [Step Name]

**Goal:** What this step achieves

```bash
# Command
kubectl describe pod <pod-name>
```

**Expected output:**

```
[Example output]
```

### Step 2: [Step Name]

**Goal:** What this step achieves

```bash
# Command
```

**Expected output:**

```
[Example output]
```

### Step 3: Restart service (if needed)

```bash
kubectl rollout restart deployment -n resilience-lab <deployment-name>
kubectl rollout status deployment -n resilience-lab <deployment-name>
```

## Verification

How to verify the problem is resolved:

```bash
# Check pod status
kubectl get pods -n resilience-lab

# Check logs
kubectl logs -n resilience-lab <pod-name> --tail=50

# Test endpoint
curl http://<service-endpoint>/healthz
```

**Success criteria:**

- [ ] Pods are in Running and Ready state
- [ ] No errors in logs
- [ ] Endpoint /healthz returns 200 OK
- [ ] Metrics returned to normal

## Rollback (if something went wrong)

```bash
# Rollback to previous version
kubectl rollout undo deployment -n resilience-lab <deployment-name>

# Or restore from backup
helm rollback resilience-lab <revision>
```

## Prevention / Long-term Fix

Long-term solution to prevent the problem in the future:

- [ ] Task 1
- [ ] Task 2
- [ ] Add monitoring/alerting

## Escalation

If the problem is not resolved after executing all steps:

1. Check related runbooks: [link to other runbooks]
2. Contact: [Slack channel / email / on-call]
3. Severity upgrade: Escalate to P0 if affecting production

## Common Pitfalls / Gotchas

- [ ] Check if old pods exist in different namespace (e.g., default)
- [ ] Check imagePullPolicy (IfNotPresent vs Always)
- [ ] NetworkPolicy: egress ≠ ingress

## Additional Resources

- [Link to documentation]
- [Link to Grafana dashboard]
- [Link to Prometheus alerts]
- [Post-mortem from previous incident]

## Change History

| Date       | Author | Changes          |
| ---------- | ------ | ---------------- |
| YYYY-MM-DD | [Name] | Created runbook |
