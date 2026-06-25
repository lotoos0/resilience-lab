# Stale deployed image silently breaks observability

**Discovered:** 2026-06-08
**Service:** API
**Context:** verifying issue #29 (rate-limit metrics & logs)

---

## What happened

While verifying that the rate-limit middleware emits structured
`rate_limit_check tenant=... path=... status=...` log lines, a Loki query
returned zero results — even after driving real traffic and real 429s through
the middleware with k6.

Pods looked completely healthy: `Running`, `/healthz` → 200,
`rl_allowed_total`/`rl_denied_total` incrementing correctly in Prometheus.
Nothing pointed at a problem. Except the one signal nobody was looking at.

## Symptoms

```bash
# Loki: zero results, no error
{app="api"} |= "rate_limit_check" | json | line_format "{{.log}}" | logfmt
# -> streams: 0
```

```bash
# Raw container logs: the line is simply never written
kubectl logs -n resilience-lab -l app.kubernetes.io/name=api --since=20m \
  | grep -c "rate_limit_check"
# -> 0
```

- Metrics: ✅ correct and incrementing
- Health checks: ✅ 200 OK
- Logs for the exact feature under test: ❌ completely absent, no error anywhere

## Why it happened

The cluster was running image `ghcr.io/lotoos0/resilience-lab-api:8b86f3d`
— built 2026-01-07, 5 months behind `develop`.

That image predates commit `1e2d70a`
(`feat(logging): add tenant context to API log lines`, merged 2026-06-07),
which added:

```python
# services/api/main.py
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
```

Without this line, application loggers propagate to the root logger which
has **no handler** under uvicorn and silently drops everything below
`WARNING`. So `logger.info("rate_limit_check ...")` never reaches stdout,
never reaches Loki, and produces zero errors in the process. The line is
just gone.

`values-dev.yaml` was still pinned to `tag: 8b86f3d` and nothing in the
deploy pipeline flagged the drift.

## Fix

Rebuilt the image from current `develop` directly inside minikube's Docker
daemon and pointed the release at it for the duration of the verification
(see [TROUBLESHOOTING_MINIKUBE_IMAGES.md](../runbooks/TROUBLESHOOTING_MINIKUBE_IMAGES.md)
and [TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md](../runbooks/TROUBLESHOOTING_HELM_FIELD_CONFLICTS.md)
for the underlying mechanics):

```bash
eval $(minikube docker-env)
docker build -t api:local -f services/api/Dockerfile .

helm upgrade resilience-lab deploy/helm/ \
  --values deploy/helm/values-dev.yaml \
  --namespace resilience-lab \
  --set api.image.repository=api \
  --set api.image.tag=local \
  --set api.image.pullPolicy=IfNotPresent \
  --force-conflicts

kubectl rollout status deployment/resilience-lab-api -n resilience-lab
```

After the rollout, the same load test produced the expected lines:

```
INFO:services.api.middleware.rate_limit:rate_limit_check tenant=verify29-v2 path=/openapi.json status=allowed count=9 limit=60
INFO:services.api.middleware.rate_limit:rate_limit_check tenant=verify29-v2 path=/openapi.json status=denied count=98 limit=60
```

`values-dev.yaml` was deliberately not updated — bumping the dev baseline
image tag is a separate release-hygiene decision, not part of verifying #29.
This rebuild was a one-off, local-only step.

## How I found it

Metrics and k6 agreed perfectly on `allowed`/`denied` counts, but Loki
showed nothing for the same time window and tenant. That asymmetry —
one observability signal present, the related one completely silent, with
zero errors in between — was the tell.

Comparing the running pod's image tag against `git log` for the relevant
source files closed the case:

```bash
kubectl get pod <pod> -n resilience-lab -o jsonpath='{.spec.containers[0].image}'
```

Image was a 5-month-old build that didn't contain the logging fix.

## Prevention

- When verifying an observability feature against a live cluster, confirm
  the deployed image actually contains the code under test — "pods are
  Running" does not mean "pods are running current code":
  ```bash
  kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[0].image}'
  git merge-base --is-ancestor <commit-that-added-the-feature> <image-tag>
  ```
- "One observability signal present, the related one silent, no errors" is
  a strong hint you're not running the code you think you're running — not
  a feature bug.
- Consider a deploy-time check that warns when a `values*.yaml` image tag
  is significantly behind `develop`/`main` for the files it deploys.
