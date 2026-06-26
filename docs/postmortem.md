# Postmortem — Resilience Lab v0.1.0

This project took longer than planned, shipped everything that was promised, and taught
me more than I expected. Here's an honest account of what happened.

---

## What This Was

A learning project built to practice SRE and DevOps patterns before they matter in
production. The goal was a working system — not a toy, not a slideshow — with two
FastAPI services, Envoy front-proxy, rate limiting, observability, and chaos testing,
all running on Kubernetes and wired up with real CI/CD.

84 pull requests. Several months. One v0.1.0 tag.

---

## What Went Well

**The Helm chart held together.** A single parent chart with two subcharts (api,
payments) plus templates for Redis, NetworkPolicy, HPA, PDB, ResourceQuota, and
LimitRange. ServiceMonitors live separately in `deploy/prometheus/` and are applied
independently. The chart rendered cleanly, deployed repeatably, and survived multiple
rounds of modification without falling apart. Getting the structure right early paid
dividends every time something needed changing.

**CI/CD was solid from the start.** CI ran lint, unit tests, integration tests, Docker
build, and Trivy image scan on every PR. CD pushed images to GHCR on branch and tag
pushes — separate workflow, separate trigger. Two Trivy suppressions were intentional
and documented (`ignore-unfixed: true` for unpatched OS-level CVEs, `skip-dirs` for
setuptools vendor copies). No corners cut.

**Envoy actually worked.** Retry policy with per-try timeout (200ms), exponential
backoff, outlier ejection, circuit breaker, and bulkhead limits — all configured and
stress-tested. Not just copied from a blog post. The latency injection scenario
produced real, unexpected data: 183/240 requests returned 504, SLO alerts never fired,
and that gap between those two facts taught me more than a clean result would have.
More on that below.

**The security baseline was real.** `runAsNonRoot: true`, `readOnlyRootFilesystem`,
`capDrop: ALL`, `allowPrivilegeEscalation: false` on every workload. ResourceQuota and
LimitRange on the namespace. Default service account with zero RBAC permissions —
confirmed with `kubectl auth can-i`. Not checkbox security.

**Observability was actually observable.** Prometheus, Grafana, Loki, Promtail — all
wired up and producing meaningful data. Recording rules for request rate, error rate,
p95 latency, retry rate, ejection rate, 429s, and bulkhead overflow. Two dashboards
with panels that reflected real system state during chaos experiments.

---

## Chaos Outcomes

### Latency injection (300ms, `tc netem`)

Injected 300ms network delay into all Payments pods via `kubectl exec`. The pre-test
expectation was that 300ms would be absorbed cleanly — Envoy's `per_try_timeout` is
200ms, so any request hitting a delayed connection would time out, retry, and
eventually exhaust retries. What actually happened:

- `upstream_cx_connect_ms P50 ≈ 305ms` — injection confirmed at the network layer
- **183/240 requests returned 504 Gateway Timeout** — `per_try_timeout` (200ms) fired,
  retries exhausted (3 attempts), client got a 504
- **Zero SLO alerts fired** — `HighErrorRate` watches the API service error rate, which
  stayed at 0 throughout; the 504s are Envoy-level only and not visible to that metric
- Cleanup left no residual state

**Verdict:** This one hurt to document honestly. The system "passed" SLO criteria while
76% of payments requests were failing — because the alerts were watching the wrong
signal. There's no alert covering Envoy-level 5xx for the payments cluster. That's an
alert coverage gap, not a resilience success. The finding is documented in
`docs/runbooks/chaos-latency-injection.md` with a suggested follow-up alert rule.

### Pod kill

Deleted a random Payments pod directly. Result:

- Recovery time: **~15 seconds** (pod scheduled, image pulled, health check passed)
- PDB (`minAvailable: 1`) returned to ALLOWED DISRUPTIONS=0 after recovery
- During the 15s window: requests to Payments would fail — Envoy had no healthy host
  to retry against (1-host cluster, `max_ejection_percent=50%` rounds to 0 ejectable)

**Verdict:** 15s recovery in a single-replica setup. With 2+ replicas Envoy could eject
the dead pod and continue serving from the healthy one — with 1 host,
`max_ejection_percent=50%` rounds to 0 ejectable, so there's nowhere to fall back.
Known limitation of single-host testing, documented in the runbook.

### Failure mode (`FAIL_MODE=1`)

Set Payments to return 500 on all requests. Result:

- Error rate visible in Grafana within one scrape interval (~15s)
- `HighErrorRate` alert fired as expected
- API propagated errors correctly — no silent swallowing

**Verdict:** Error propagation path works. Observability caught it immediately.

---

## What I'd Do Differently

**PostgreSQL shouldn't be in the chart.** It's in `values.yaml`, wired into env vars,
but neither service actually uses it. Payments was originally going to be
PostgreSQL-backed; that got cut during development but the scaffolding stayed.
Six months later I was closing backup-script issues because "the database we're not
using doesn't need backups." Remove it, or actually use it.

**Scope decisions should happen earlier.** I opened 20+ issues at milestone planning
time and ended up closing half of them without doing the work — CHANGELOG ceremony,
pre-release checklists, demo GIFs, backup scripts, dashboard polish for filters that
don't exist. The ones worth doing were obvious from the start. The ones that weren't
took a full triage session to recognize. Better to start with fewer, well-scoped issues
and add more than to bulk-create and then prune.

**The timeline slipped — and that's fine, but be honest about it.** This was a solo
learning project with no deadline that mattered. The real problem wasn't slipping, it
was writing milestone plans with optimistic dates and then not updating them when they
became fiction. A stale `CURRENT_PLAN.md` with past-due dates is worse than no plan.

**Tests targeted the wrong endpoints.** The k6 rate-limit smoke test was running
against an endpoint excluded from the rate limiter — so tests were always green for the
wrong reason. That's a classic case of testing the implementation you have, not the
behavior you want. Fixed before release, but it cost time.

---

## What v0.2.0 Looks Like

These are the things deferred from v0.1.0 that are actually worth doing:

- **OpenTelemetry tracing** — metrics and logs are in place; traces are the missing
  signal. Instrument API and Payments with OTLP, wire up Jaeger or an OTel Collector,
  see a real API → Payments trace. Learning goal, not vanity.
- **Full egress NetworkPolicy** — egress is currently partially constrained (DNS +
  ports 8000/8001/6379 allowed broadly). Proper per-service egress rules would close
  the gap in the security baseline.
- **Actually use PostgreSQL or remove it entirely** — the half-in, half-out state is
  worse than either option.

---

## Final Thought

Everything that was promised in the v0.1.0 milestone shipped. The system breaks in
the ways it's supposed to break and recovers in the ways it's supposed to recover.
The observability stack shows you what's happening when it does. That was the goal.

The rest is just cleanup.
