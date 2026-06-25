# Security

*Last updated: 2026-06-25*

Container security is one of the few places where "good enough" quietly turns into "incident report". Here's what I put in place, why I made each call, and what I'm still ignoring on purpose.

---

## Table of Contents

- [Container Image Scanning (Trivy)](#container-image-scanning-trivy)
- [Known Findings (accepted / not actionable)](#known-findings-accepted--not-actionable)
- [Python Dependency Pins](#python-dependency-pins-security-motivated)
- [Dockerfile Upgrade Step](#dockerfile-upgrade-step)
- [Runtime Security Baseline](#runtime-security-baseline)
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

All workloads in `deploy/helm/` enforce:

- non-root user (`runAsNonRoot: true`, `runAsUser: 1000`)
- read-only root filesystem (`readOnlyRootFilesystem: true`)
- all Linux capabilities dropped (`drop: ["ALL"]`)
- `allowPrivilegeEscalation: false`

NetworkPolicies restrict pod-to-pod traffic to declared paths only.
See `deploy/helm/templates/netpol-*.yaml`.

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
