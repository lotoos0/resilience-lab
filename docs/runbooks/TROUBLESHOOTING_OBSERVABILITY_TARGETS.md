> This runbook was created from a real v0.1.0 observability validation incident.

# Runbook: Prometheus targets missing or firing after observability setup

**Status:** Active

**Owner:** DevOps Team

**Last Updated:** 2026-06-03

**Severity:** P2 (Observability degradation)

## Description

Prometheus alert rules are installed, but `resilience-lab` targets are missing, down, or firing alerts such as `APIDown` and `PrometheusTargetDown`.

This runbook covers the full troubleshooting path:

- ServiceMonitors exist but no `resilience-lab` targets appear in Prometheus.
- API `/metrics` returns `500`.
- API metrics target is discovered but remains `DOWN`.
- Helm upgrade conflicts with HPA-managed replicas.
- Minikube control-plane targets are down and create noise.

## Impact / Blast Radius

- Affected: Prometheus targets, alerts, dashboards, and observability validation.
- User-facing traffic impacted: usually no.
- Release impact: blocks observability issues such as basic alerting and scrape target verification.

## Symptoms

Prometheus `/targets` shows:

- only `kube-system` and `monitoring` targets;
- no targets with `namespace="resilience-lab"`;
- `resilience-lab-api` target is present but `DOWN`;
- kube-prometheus-stack control-plane targets are `DOWN`, such as:
  - `kube-controller-manager`
  - `kube-scheduler`
  - `kube-etcd`

Prometheus `/alerts` shows:

- `APIDown` firing;
- `PrometheusTargetDown` firing;
- `HighErrorRate` is healthy or inactive.

API logs may show:

```text
redis.exceptions.ConnectionError: Error -2 connecting to redis:6379. Name or service not known.
```

Helm upgrade may fail with:

```text
conflict with "kube-controller-manager" with subresource "scale" using apps/v1: .spec.replicas
```

## Root Causes Observed

### 1. Application targets were not deployed

ServiceMonitors were present in the `monitoring` namespace, but there were no Services or Endpoints in the `resilience-lab` namespace.

Observed output:

```text
kubectl get svc -n resilience-lab
No resources found in resilience-lab namespace.

kubectl get endpoints -n resilience-lab
No resources found in resilience-lab namespace.
```

### 2. Envoy is deployed outside the Helm chart

API and Payments are deployed through Helm, but Envoy manifests live under `deploy/envoy/` and must be applied separately.

If Envoy is not applied, the Envoy ServiceMonitor has no target.

### 3. API `/metrics` depended on Redis through rate limiting middleware

The API rate-limit middleware attempted Redis access before serving `/metrics`. If Redis DNS/service/connectivity failed, Prometheus received HTTP 500.

The fix is to bypass rate limiting for operational endpoints:

- `/healthz`
- `/metrics`

### 4. New code was built locally but not deployed into the running cluster

Restarting a Deployment does not update code unless the pod image changes and the cluster can pull or access that image.

In Minikube, either:

- build into Minikube's Docker daemon; or
- push to a registry and update the Deployment image tag.

### 5. Helm upgrade conflicted with HPA-managed replicas

When HPA manages the Deployment scale subresource, Helm/server-side apply can conflict on `.spec.replicas`.

This blocks an image rollout through Helm even when the manifest is otherwise valid.

### 6. Minikube control-plane target noise

kube-prometheus-stack may discover Minikube control-plane targets that refuse connections:

- `kube-controller-manager`
- `kube-scheduler`
- `kube-etcd`

These are separate from Resilience Lab application monitoring. They can be cleaned up later, but they should not block validation of `resilience-lab` targets.

## Diagnosis

### Step 1: Check namespace labels

```bash
kubectl get ns --show-labels
```

Expected:

- `monitoring` namespace exists.
- `resilience-lab` namespace exists.

### Step 2: Check ServiceMonitors

```bash
kubectl get servicemonitor -A
```

Expected:

```text
monitoring   resilience-lab-api-metrics
monitoring   envoy-proxy-metrics
```

### Step 3: Check application Services and Endpoints

```bash
kubectl get svc -n resilience-lab --show-labels
kubectl get endpoints -n resilience-lab
kubectl get pods -n resilience-lab -o wide
```

Expected:

- API Service exists.
- Envoy Service exists.
- API and Envoy Endpoints exist.
- API pods are `Running` and `Ready`.

### Step 4: Check ServiceMonitor selectors

```bash
kubectl describe servicemonitor -n monitoring resilience-lab-api-metrics
kubectl describe servicemonitor -n monitoring envoy-proxy-metrics
```

Expected selector matches:

- API Service label: `app.kubernetes.io/name: api`
- Envoy Service label: `app: envoy-proxy`

### Step 5: Test `/metrics` from inside the cluster

From the same namespace:

```bash
kubectl run curl-test -n resilience-lab --rm -it \
  --image=curlimages/curl --restart=Never -- \
  curl -v http://resilience-lab-api:8000/metrics
```

From the monitoring namespace:

```bash
kubectl run curl-test -n monitoring --rm -it \
  --image=curlimages/curl --restart=Never -- \
  curl -v http://resilience-lab-api.resilience-lab.svc.cluster.local:8000/metrics
```

Expected:

```text
HTTP/1.1 200 OK
```

### Step 6: Check API logs

```bash
kubectl logs -n resilience-lab deployment/resilience-lab-api --tail=100
```

If logs show Redis errors while scraping `/metrics`, verify that the running image contains the operational endpoint bypass.

## Resolution

### Case A: ServiceMonitors exist but no `resilience-lab` Services exist

Deploy the Helm chart:

```bash
helm dependency build deploy/helm
helm upgrade --install resilience-lab deploy/helm \
  --values deploy/helm/values-dev.yaml \
  --namespace resilience-lab \
  --create-namespace
```

Apply Envoy separately:

```bash
kubectl apply -f deploy/envoy/envoy-config.yaml
kubectl apply -f deploy/envoy/envoy-deployment.yaml
kubectl apply -f deploy/envoy/envoy-service.yaml
```

Verify:

```bash
kubectl get svc -n resilience-lab --show-labels
kubectl get endpoints -n resilience-lab
```

### Case B: API `/metrics` returns 500

Ensure the API image includes the rate-limit bypass for:

- `/healthz`
- `/metrics`

The code should bypass Redis before `_check_rate_limit()` for these paths.

Build and deploy a new image. In Minikube:

```bash
eval $(minikube docker-env)

docker build -t ghcr.io/lotoos0/resilience-lab-api:metrics-bypass \
  -f services/api/Dockerfile .
```

If Helm upgrade conflicts with HPA, update the image directly:

```bash
kubectl -n resilience-lab set image deployment/resilience-lab-api \
  api=ghcr.io/lotoos0/resilience-lab-api:metrics-bypass
```

Then verify rollout:

```bash
kubectl -n resilience-lab rollout status deployment/resilience-lab-api
kubectl -n resilience-lab get pods -l app.kubernetes.io/name=api
```

### Case C: Helm upgrade fails on `.spec.replicas`

Short-term workaround:

```bash
kubectl -n resilience-lab set image deployment/resilience-lab-api \
  api=<new-image-tag>
```

Long-term fix:

- adjust Helm/HPA ownership so Helm does not fight HPA over `.spec.replicas`;
- or temporarily disable HPA during Helm upgrades;
- or template `replicas` only when autoscaling is disabled.

### Case D: kube-system control-plane targets are DOWN in Minikube

This is common in local Minikube setups. It is separate from Resilience Lab target health.

For local lab cleanup, consider disabling these kube-prometheus-stack monitors:

```yaml
kubeControllerManager:
  enabled: false

kubeScheduler:
  enabled: false

kubeEtcd:
  enabled: false
```

Apply the values through the kube-prometheus-stack Helm release.

## Verification

In Prometheus, run:

```promql
up{namespace="resilience-lab"}
```

Expected:

- API target is `1`.
- Envoy target is `1`.

Check alerts:

```text
http://localhost:9090/alerts
```

Expected:

- `HighErrorRate` is green/inactive.
- `APIDown` is green/inactive.
- `PrometheusTargetDown` is green/inactive.

## Prevention

- Keep `ServiceMonitor` manifests applied with the observability stack.
- Include Envoy deployment in the main release flow or document it as a separate required apply step.
- Keep `/healthz` and `/metrics` independent from Redis and other optional dependencies.
- Use explicit image tags during validation; avoid relying on stale `latest` or `IfNotPresent`.
- Add a Helm/HPA compatibility fix before release.
- Add this runbook to observability validation steps.

## Related Issues

- `#39` - Basic Prometheus alert rules
- `#34` - Verify Prometheus scrape targets
- `#29` - Expose rate-limit metrics and logs
- `#38` - Deploy Loki + Promtail

## Additional Resources

- [Observability Overview](../observability.md)
- [Prometheus scrape troubleshooting](./TROUBLESHOOTING_PROMETHEUS_SCRAPE.md)
- [Prometheus Rules](../../deploy/prometheus/rules.yaml)
- [API ServiceMonitor](../../deploy/prometheus/servicemonitor-api.yaml)
- [Envoy ServiceMonitor](../../deploy/prometheus/servicemonitor-envoy.yaml)

## Change History

| Date       | Author     | Changes |
|------------|------------|---------|
| 2026-06-03 | DevOps Team | Created after v0.1.0 alert validation incident |
