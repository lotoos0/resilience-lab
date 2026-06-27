# Security

*Last updated: 2026-06-26*

Container security is one of the few places where "good enough" quietly turns into "incident report". Here's what I put in place, why I made each call, and what I'm still ignoring on purpose.

---

## Table of Contents

- [Container Image Scanning (Trivy)](#container-image-scanning-trivy)
- [Known Findings (accepted / not actionable)](#known-findings-accepted--not-actionable)
- [Python Dependency Pins](#python-dependency-pins-security-motivated)
- [Dockerfile Upgrade Step](#dockerfile-upgrade-step)
- [Runtime Security Baseline](#runtime-security-baseline)
- [Namespace Resource Constraints](#namespace-resource-constraints)
- [RBAC Verification](#rbac-verification)
- [Open Items](#open-items)
- [What changed in this document](#what-changed-in-this-document)

---

## Container Image Scanning (Trivy)

Every CI run scans both the source tree and the built images using Trivy
(`aquasecurity/trivy-action@v0.36.0`). I run two scan types with different configs
because they serve different purposes.

### Filesystem scan

```yaml
scan-type: fs
scan-ref: '.'
format: sarif
```

No `exit-code: 1` here — the filesystem scan is informational and uploads results to
the GitHub Security tab as SARIF. The hard gate is on the built image (below), where
I actually know what the final dependency set looks like.

### Image scan (API + Payments)

Both images go through the same config:

```yaml
exit-code: '1'
ignore-unfixed: true
severity: CRITICAL,HIGH
skip-dirs: '**/setuptools/_vendor'
```

**`ignore-unfixed: true`** — CVEs without an upstream fix don't block CI. The base
`python:3.11-slim` (Debian 13 "Trixie") ships packages like `perl-base` and
`libncursesw6` with known CVEs that Debian hasn't patched yet. Failing CI on
unfixable OS-level noise would just train the team to ignore CI failures — which is
a worse outcome than the CVEs themselves.

**`skip-dirs: '**/setuptools/_vendor'`** — setuptools bundles internal copies of
`wheel` and `jaraco.context` inside its `_vendor/` directory. These are not runtime
dependencies and can't be upgraded via pip. Trivy finds them anyway and flags them as
vulnerabilities. Skipping `_vendor/` stops the false-positive flood without hiding
anything real — the standalone copies of these packages in `site-packages` are pinned
to patched versions (see table below).

---

## Known Findings (accepted / not actionable)

These are the CVEs I'm currently sitting on intentionally:

| Package | CVE | Severity | Status | Notes |
|---------|-----|----------|--------|-------|
| `perl-base` | CVE-2026-42496, CVE-2026-8376, CVE-2026-42497, CVE-2026-48962, CVE-2026-9538 | CRITICAL / HIGH | No fix in Debian 13 | Suppressed via `ignore-unfixed: true`. Perl is part of the Debian slim base — removing it risks breaking apt in the build layer. 5 CVEs, all unpatched upstream. |
| `libncursesw6` | CVE-2025-69720 | HIGH | No fix in Debian 13 | Same rationale. |
| `setuptools/_vendor/wheel` | CVE-2026-24049 | HIGH | Vendored copy, not runtime | Suppressed via `skip-dirs`. The standalone `wheel` package in site-packages is pinned to `>=0.46.2` (patched). |
| `setuptools/_vendor/jaraco.context` | CVE-2026-23949 | HIGH | Vendored copy, not runtime | Suppressed via `skip-dirs`. Standalone `jaraco.context` in site-packages is pinned to `>=6.1.0` (patched). |

---

## Python Dependency Pins (security-motivated)

These are pinned explicitly in `requirements.txt` to override vulnerable transitive
versions. Pip would otherwise happily resolve an older, vulnerable release:

| Package | Pin | CVEs fixed |
|---------|-----|-----------|
| `wheel` | `>=0.46.2` | CVE-2026-24049 |
| `jaraco.context` | `>=6.1.0` | CVE-2026-23949 |
| `starlette` | `==1.3.1` | CVE-2026-48818, CVE-2026-54283 (supersedes the earlier `1.0.1` pin, which itself fixed CVE-2025-62727) |

---

## Dockerfile Upgrade Step

Both service Dockerfiles run an explicit wheel upgrade before the main `pip install`:

```dockerfile
RUN pip install --upgrade "wheel>=0.46.2" && \
    pip install --no-cache-dir -r requirements.txt
```

This is defense-in-depth. The primary fix for the `wheel` CVE finding is already the
`skip-dirs` suppression plus the `requirements.txt` pin. The `--upgrade` step covers
an edge case: packages pre-installed in the base image layer aren't always upgraded by
`pip install -r requirements.txt` without `--upgrade`, even when the pinned constraint
demands a higher version.

---

## Runtime Security Baseline

Default service workloads (API, Payments) in `deploy/helm/` enforce:

- non-root user (`runAsNonRoot: true`, `runAsUser: 1000`)
- read-only root filesystem (`readOnlyRootFilesystem: true`)
- all Linux capabilities dropped (`drop: ["ALL"]`)
- `allowPrivilegeEscalation: false`

Two known exceptions: Redis runs as `runAsUser: 999` (upstream image convention,
`redis-deployment.yaml:24`). Chaos mode (`values-chaos.yaml`) deliberately relaxes
these constraints — `runAsUser: 0` and `NET_ADMIN` are required for fault injection
to work. That's intentional and scoped to chaos testing only.

NetworkPolicies enforce ingress as default-deny with explicit allows per service.
Egress is partially constrained — DNS plus ports 8000, 8001, and 6379 are allowed
broadly by port (`netpol-allow-essentials.yaml:10`). Full egress control is deferred;
see [Open Items](#open-items) and issue #44.

---

## Namespace Resource Constraints

I added two new Helm templates in `deploy/helm/templates/` as part of the v0.1.0
security review: `resourcequota.yaml` and `limitrange.yaml`. These didn't exist before.
The cluster was running on the honour system — every workload could theoretically eat
as much CPU and memory as it wanted, and nothing would stop it.

That's fine for a local dev sandbox. Less fine when you're writing a document called "Security".

### ResourceQuota

A `ResourceQuota` puts a hard ceiling on the entire `resilience-lab` namespace. The
numbers aren't arbitrary — here's exactly why each one landed where it did:

| What | Why that number |
|------|-----------------|
| `limits.cpu: "4"` | HPA can scale api and payments to 4 replicas each. 4 replicas × 500m limit = 2 cores per service, 2 services = 4 cores. Redis adds 250m on top — there's slack, but it's not a blank cheque. |
| `requests.cpu: "1"` | Baseline at 2 replicas: 2×100m (api) + 2×100m (payments) + 50m (redis) = 450m. Rounded up to 1 to absorb the brief overlap when HPA spins up a new pod before the old one terminates. |
| `limits.memory: 4Gi` | Same HPA headroom: 4 replicas × 512Mi × 2 services = 4Gi exactly. Redis adds 256Mi on top — so this cap is intentionally tight. If the namespace needs more than 4Gi, something has gone sideways. |
| `requests.memory: 1Gi` | Baseline: 2×128Mi + 2×128Mi + 64Mi = 448Mi. Rounded to 1Gi for the same pod-transition reason as CPU. |

Object count caps — 20 pods, 10 services, 20 configmaps, 20 secrets, 5 PVCs — are
generous enough to not get in the way of normal operations, but tight enough to notice
if something starts spinning up resources in a loop.

### LimitRange

A `LimitRange` covers the per-container side of the problem. Without it, a pod that
doesn't declare resource limits at all gets scheduled as unbounded — it can spike to
whatever the node allows, completely bypassing the ResourceQuota. Kubernetes is helpful
like that.

| | CPU | Memory |
|-|-----|--------|
| default limit | 500m | 512 Mi |
| default request | 100m | 128 Mi |
| max | 1 core | 1 Gi |
| min | 10m | 16 Mi |

The `default` values mirror what api and payments already declare explicitly in their
`values.yaml` — so existing workloads are unaffected. The `max` ceiling means no
single container can sneak past 1 core or 1 Gi of RAM, which is especially useful
when a future workload lands in the namespace without carefully reviewed resource specs.

---

## RBAC Verification

None of the deployed workloads — api, payments, redis — need to talk to the Kubernetes
API. They're not operators, they're not controllers, they're web services that talk
HTTP and Redis. So I added zero RoleBindings for the default service account. On purpose.

`kubectl auth can-i` confirms it:

```
kubectl auth can-i create pods \
  --as=system:serviceaccount:resilience-lab:default -n resilience-lab
# → no

kubectl auth can-i delete pods \
  --as=system:serviceaccount:resilience-lab:default -n resilience-lab
# → no

kubectl auth can-i get secrets \
  --as=system:serviceaccount:resilience-lab:default -n resilience-lab
# → no

kubectl auth can-i list pods \
  --as=system:serviceaccount:resilience-lab:default -n resilience-lab
# → no
```

Four `no`s. That's the goal. The default SA can't create or delete workloads, can't
read secrets, can't even list other pods in the same namespace. If a pod gets
compromised, the blast radius is limited to whatever that container can reach over the
network — not the entire cluster.

If a future component genuinely needs Kubernetes API access (a controller, a sidecar
injector, something that actually has business talking to the API server), it gets a
dedicated service account with a scoped `Role` covering exactly the verbs it needs.
The default SA stays at zero.

---

## Open Items

See [GitHub Issue #43](https://github.com/lotoos0/resilience-lab/issues/43) for the
full v0.1.0 security review checklist.

Deferred to post-v0.1.0:

- network egress control (#44)
- runtime security and audit logging (Falco / AuditPolicy) (#45)

---

## What changed in this document

The original file was written during M1/M2 and never updated after the CI pipeline
matured. Three things were wrong:

| # | Severity | What was wrong | What it is now |
|---|---|---|---|
| 1 | High | Trivy version listed as `@master` v0.71.0 | Actual CI uses `@v0.36.0` (pinned, not floating) |
| 2 | High | Filesystem scan shown with `exit-code: 1`, `ignore-unfixed: true`, `skip-dirs` | FS scan is informational only — those 3 params apply exclusively to the image scans |
| 3 | High | Starlette pinned at `==0.49.1` fixing CVE-2025-62727 | `requirements.txt` has `==1.3.1` fixing CVE-2026-48818 + CVE-2026-54283 (2 newer CVEs, pin bumped June 2026) |

Everything else — `wheel` pin, `jaraco.context` pin, Dockerfile upgrade step, runtime
baseline, open items — was accurate and unchanged.
