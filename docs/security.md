# Security

This document covers the security baseline and known findings for Resilience Lab.

---

## Container Image Scanning (Trivy)

Images are scanned on every CI run using [Trivy](https://trivy.dev/) (`aquasecurity/trivy-action@master`, v0.71.0).

### Scan configuration

```yaml
severity: CRITICAL,HIGH
exit-code: 1
ignore-unfixed: true
skip-dirs: '**/setuptools/_vendor'
```

**`ignore-unfixed: true`** — CVEs with no available fix in the upstream package repository do not block CI. Rationale: the base `python:3.11-slim` (Debian 13 "Trixie") ships packages such as `perl-base` and `libncursesw6` that have known CVEs with no Debian patch yet. Blocking CI on unfixable OS-level CVEs creates noise without actionable remediation.

**`skip-dirs: '**/setuptools/_vendor'`** — Trivy scans `setuptools`' internal `_vendor` directory, which contains pinned copies of packages (`wheel`, `jaraco.context`, etc.) bundled for setuptools' own use. These are not runtime dependencies of the application and cannot be upgraded via pip. Skipping this directory prevents false-positive findings from internal setuptools tooling.

### Known findings (accepted / not actionable)

| Package | CVE | Severity | Status | Notes |
|---------|-----|----------|--------|-------|
| `perl-base` | CVE-2026-42496, CVE-2026-8376, CVE-2026-42497, CVE-2026-48962, CVE-2026-9538 | CRITICAL / HIGH | No fix in Debian 13 | Suppressed via `ignore-unfixed: true`. Perl is part of the Debian slim base; removal risks breaking apt tooling in the build layer. |
| `libncursesw6` | CVE-2025-69720 | HIGH | No fix in Debian 13 | Same suppression. |
| `setuptools/_vendor/wheel` | CVE-2026-24049 | HIGH | Vendored copy | Suppressed via `skip-dirs`. Standalone `wheel` package in site-packages is pinned to `>=0.46.2`. |
| `setuptools/_vendor/jaraco.context` | CVE-2026-23949 | HIGH | Vendored copy | Suppressed via `skip-dirs`. Standalone `jaraco.context` in site-packages is pinned to `>=6.1.0`. |

### Python dependency pins (security-motivated)

The following packages are explicitly pinned in `requirements.txt` to override vulnerable transitive versions:

| Package | Minimum version | CVE fixed |
|---------|----------------|-----------|
| `wheel` | `>=0.46.2` | CVE-2026-24049 |
| `jaraco.context` | `>=6.1.0` | CVE-2026-23949 |
| `starlette` | `==0.49.1` | CVE-2025-62727 |

### Dockerfile upgrade step

Both service Dockerfiles include an explicit upgrade before the main `pip install` to ensure the base image's pre-installed `wheel` is replaced:

```dockerfile
RUN pip install --upgrade "wheel>=0.46.2" && \
    pip install --no-cache-dir -r requirements.txt
```

Without the explicit `--upgrade` step, `pip install -r requirements.txt` does not upgrade packages already present in the base image layer, even when the version constraint is not satisfied.

---

## Runtime Security Baseline

All workloads in `deploy/helm/` enforce:

- non-root user (`runAsNonRoot: true`, `runAsUser: 1000`)
- read-only root filesystem (`readOnlyRootFilesystem: true`)
- all Linux capabilities dropped (`drop: ["ALL"]`)
- `allowPrivilegeEscalation: false`

NetworkPolicies restrict pod-to-pod traffic to declared paths only. See `deploy/helm/templates/netpol-*.yaml`.

---

## Open Items

See [GitHub Issue #43](https://github.com/lotoos0/resilience-lab/issues/43) for the full v0.1.0 security review checklist.

Deferred to post-v0.1.0:

- network egress control (#44)
- runtime security and audit logging (Falco / AuditPolicy) (#45)
