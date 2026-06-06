# Runbook: Helm SSA Field Manager Conflicts

**Status:** Active
**Owner:** lotoos0
**Last Updated:** 2026-06-06
**Severity:** P2 (Medium)

## Description

`helm upgrade` fails with a `conflict occurred while applying object` error because fields in a deployment have a different field manager than Helm. This happens when `kubectl set image`, `kubectl apply`, or `kubectl scale` was used directly on resources managed by Helm.

## Impact / Blast Radius

- Which components are affected: any deployment managed by Helm
- Does the problem affect end users: NO (cluster runs fine, only `helm upgrade` is blocked)
- Is this observability-only issue: NO

## Symptoms

`helm upgrade` fails with an error like:

```
Error: UPGRADE FAILED: conflict occurred while applying object resilience-lab/resilience-lab-api apps/v1, Kind=Deployment:
Apply failed with 2 conflicts:
  conflicts with "kubectl-set" using apps/v1:
  - .spec.template.spec.containers[name="api"].image
  conflicts with "kube-controller-manager" using apps/v1:
  - .spec.replicas
```

or:

```
conflicts with "before-first-apply" using apps/v1:
- .spec.replicas
- .spec.template.spec.containers[name="api"].image
```

## Root Cause

Kubernetes Server-Side Apply (SSA) tracks the "owner" (field manager) of every field in an object. When you use `kubectl` directly on a Helm-managed resource, Kubernetes records a different owner for the modified fields:

- `kubectl set image` → field manager: `kubectl-set`
- `kubectl apply` → field manager: `before-first-apply`
- HPA managing replicas → field manager: `kube-controller-manager`

On the next `helm upgrade`, Helm detects the conflicts and refuses to overwrite those fields.

## Pre-flight Checks

```bash
# Check current field managers on the deployment
kubectl get deployment <name> -n resilience-lab \
  -o jsonpath='{.metadata.managedFields[*].manager}' | tr ' ' '\n'
```

If you see `kubectl-set`, `before-first-apply`, or anything other than `helm` — problem confirmed.

## Resolution Steps

### Step 1: Make sure values.yaml reflects the actual cluster state

Before fixing, check what images are actually running:

```bash
kubectl get deployment <name> -n resilience-lab \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Update the corresponding `values.yaml` so the tag matches what is running. Otherwise `--force-conflicts` will deploy the wrong image.

### Step 2: Restore Helm ownership

```bash
helm upgrade resilience-lab deploy/helm/ -n resilience-lab --force-conflicts
```

`--force-conflicts` tells Kubernetes to transfer ownership of all conflicting fields to Helm. Pods are **not restarted** if the field values do not change.

**Expected output:**

```
Release "resilience-lab" has been upgraded. Happy Helming!
STATUS: deployed
```

### Step 3: Verify

```bash
# Helm should now be the only field manager
kubectl get deployment <name> -n resilience-lab \
  -o jsonpath='{.metadata.managedFields[*].manager}' | tr ' ' '\n'
```

## Verification

```bash
# Subsequent upgrades should work without any extra flags
helm upgrade resilience-lab deploy/helm/ -n resilience-lab

# Pods are running correctly
kubectl get pods -n resilience-lab
```

## Prevention / Long-term Fix

- Never use `kubectl set image`, `kubectl apply`, or `kubectl scale` on resources managed by Helm
- Image changes: always via `values.yaml` + `helm upgrade`
- Scaling: via `values.yaml` (replicaCount) or let HPA manage replicas — but then do not set `replicaCount` in values

## Common Pitfalls / Gotchas

- `--force` is **deprecated** in newer Helm and **does not work** with SSA — produces `cannot use server-side apply and force replace together`
- Clearing `managedFields` via `kubectl patch` and removing the `last-applied-configuration` annotation is **not enough** — `before-first-apply` persists
- `--force-conflicts` is the only reliable fix

## Change History

| Date       | Author  | Changes         |
| ---------- | ------- | --------------- |
| 2026-06-06 | lotoos0 | Created runbook |
