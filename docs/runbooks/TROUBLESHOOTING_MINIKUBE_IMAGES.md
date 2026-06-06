# Runbook: Minikube — ImagePullBackOff for Local Images

**Status:** Active
**Owner:** lotoos0
**Last Updated:** 2026-06-06
**Severity:** P2 (Medium)

## Description

A pod is stuck in `ImagePullBackOff` because the minikube cluster cannot pull an image from an external registry (image does not exist, no access), or the image was built locally on the host but never made it inside minikube.

## Impact / Blast Radius

- Which components are affected: any deployment with an unreachable image
- Does the problem affect end users: YES (pod does not start, service unavailable)
- Is this observability-only issue: NO

## Symptoms

```bash
kubectl get pods -n resilience-lab
# NAME                                     READY   STATUS             RESTARTS   AGE
# resilience-lab-payments-7f78b8764-67dvh  0/1     ImagePullBackOff   0          3d1h
```

```bash
kubectl logs -n resilience-lab <pod-name>
# Error from server (BadRequest): container "payments" is waiting to start: trying and failing to pull image
```

## Root Cause

Minikube has its **own isolated Docker daemon** — separate from the system Docker on the host. An image built with `docker build` on the host is not visible inside the minikube cluster.

Additionally, `values.yaml` may have a wrong `repository` or `tag` pointing to a non-existent image in an external registry.

## Pre-flight Checks

```bash
# Check pod status
kubectl get pods -n resilience-lab -l app.kubernetes.io/name=<service>

# Check which image the pod is trying to pull
kubectl get deployment <name> -n resilience-lab \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check if the image exists in the host Docker
docker images | grep <image-name>
```

## Resolution Steps

### Step 1: Point your terminal at minikube's Docker daemon

```bash
eval $(minikube docker-env)
```

After this, all `docker` commands go to the Docker inside minikube, not the system one.

**Verify:**

```bash
docker info | grep "Name:"
# Should show the minikube VM name, not the host hostname
```

### Step 2: Build the image inside minikube

```bash
docker build -f services/<service>/Dockerfile -t <image-name>:local .
```

The image lands directly in the cluster — no import step needed.

### Step 3: Update values.yaml

In `deploy/helm/charts/<service>/values.yaml`:

```yaml
image:
  repository: <image-name>
  tag: local
  pullPolicy: IfNotPresent
```

`IfNotPresent` — the cluster uses the local image and does not attempt to pull from a registry.

### Step 4: Deploy the updated image

```bash
# If helm upgrade works normally:
helm upgrade resilience-lab deploy/helm/ -n resilience-lab

# If helm has field manager conflicts (see TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md):
kubectl set image deployment/<name> \
  <container>=<image-name>:local \
  -n resilience-lab
```

### Step 5: Return to the system Docker

```bash
eval $(minikube docker-env --unset)
```

## Verification

```bash
kubectl get pods -n resilience-lab -l app.kubernetes.io/name=<service>
# STATUS should be Running

kubectl logs -n resilience-lab -l app.kubernetes.io/name=<service> --tail=20
```

**Success criteria:**

- [ ] Pod in `Running` and `Ready` state
- [ ] No ImagePull errors in logs
- [ ] `/healthz` endpoint returns 200

## Prevention / Long-term Fix

- Always build images via `eval $(minikube docker-env)` when working with a local cluster
- Set `pullPolicy: IfNotPresent` for local images — never `Always` (forces pull from registry)
- Use a consistent tag (`local`) for local builds to distinguish them from registry images

## Common Pitfalls / Gotchas

- `eval $(minikube docker-env)` applies only to the current terminal session — repeat it in every new terminal
- `pullPolicy: Always` ignores local images and always tries to pull from a registry — do not use with local builds
- For k3d instead of minikube: `k3d image import <image> -c <cluster>`

## Additional Resources

- [TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md](TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md) — if helm upgrade fails after building the image

## Change History

| Date       | Author  | Changes         |
| ---------- | ------- | --------------- |
| 2026-06-06 | lotoos0 | Created runbook |
