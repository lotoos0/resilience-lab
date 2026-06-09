# GitHub Issue Triage

**Created:** June 3, 2026
**Repository:** `lotoos0/resilience-lab`
**Scope:** Open GitHub Issues `#29`-`#57`
**Plan source:** `docs/CURRENT_PLAN.md`
**GitHub sync status:** Applied on June 3, 2026

This document started as an offline triage pass. The first GitHub cleanup batch has now been applied.

Applied changes:

- Created `#59` as the post-v0.1.0 deferred enhancements backlog.
- Closed `#32`, `#33`, `#44`, `#45`, `#47`, and `#48` as `not_planned` for v0.1.0.
- Rewrote `#39` from advanced SLO/burn-rate scope to basic v0.1.0 Prometheus alerts.
- Closed `#39` as completed after runtime validation.
- Renamed active issues to use `[v0.1.0]` instead of stale `DAYxx` titles.
- Confirmed `#38` Loki + Promtail as v0.1.0 scope.
- Created `#60` for a minimal OpenTelemetry tracing baseline as a v0.1.0 stretch item.

## Decision Labels

- `done`: repository appears to satisfy the issue; close after one verification comment.
- `partial`: repository contains some implementation, but acceptance criteria are not fully met or not verified.
- `v0.1.0`: keep in the active MVP release backlog.
- `post-v0.1.0`: keep as future scope; do not block v0.1.0.
- `superseded`: replace with a current-plan issue or close with a superseded note.

## Summary

The GitHub backlog is older than `docs/CURRENT_PLAN.md`. The active v0.1.0 backlog should focus on:

- completing observability MVP: Prometheus scrape correctness, Grafana dashboards, basic alert rules, Loki/Promtail logging, and a minimal OpenTelemetry tracing baseline if scope allows;
- finishing backup/restore and operational runbooks;
- validating chaos scenarios that demonstrate resilience without adding a new chaos platform;
- release prep: changelog, release notes, final docs, demo, validation, and tag.

Do not treat the old `DAYxx` sequence as the delivery order. Use it as raw backlog material.

## Issue Decisions

| Issue | Title | Decision | Recommended action | Repo evidence / notes |
| --- | --- | --- | --- | --- |
| #29 | `[v0.1.0] Expose rate-limit metrics and logs` | done | Verified end-to-end on minikube (2026-06-08); close. | All 4 ACs confirmed live: `rl_allowed_total`/`rl_denied_total` in Prometheus, `rate_limit_check tenant=... path=... status=...` lines in Loki, and a k6 run against `/openapi.json` produced 40-41× HTTP 429 (`rate_limit_exceeded`) — k6, Prometheus, and Loki counts matched exactly (allowed=111, denied=40/41) for the same tenant. README now documents usage/headers (`tests/load/rate-limit-test*.js`, `docs/M3_RESILIENCE_PATTERNS.md`). **Note:** AC #2 (logs) initially showed nothing in Loki because the cluster was running a stale API image (`8b86f3d`, 2026-01-07) that predates `1e2d70a` (`feat(logging): add tenant context`, the commit that added `logging.basicConfig` so `rate_limit_check` lines reach stdout). Verification required a one-off local rebuild+redeploy (`api:local` via `eval $(minikube docker-env)` + `helm upgrade --set api.image.repository=api --set api.image.tag=local --force-conflicts`); `values-dev.yaml` (still pinned to `8b86f3d`) was deliberately left unchanged — updating the dev baseline image tag is a separate release-hygiene concern, not in scope for #29. Also found and noted separately (not fixed here): `GET /` returns 500 (`ResponseValidationError` — `endpoints` field declared `Dict[str, str]` but returns a list). |
| #30 | `[v0.1.0] Validate Envoy bulkhead limits` | partial, v0.1.0 | Keep open until stress evidence is captured. | Envoy circuit breaker thresholds exist in `deploy/envoy/envoy-config.yaml`. Need stress test output proving bounded queueing and rejected/overflow counters. |
| #31 | `[v0.1.0] Tune retries and timeouts` | partial, v0.1.0 | Keep open; align config and docs. | Envoy has `num_retries: 2`, but `per_try_timeout` is `2s`, while the issue expects about `200ms`. Needs explicit tuning decision and validation. |
| #32 | `[post-v0.1.0] Implement canary routing by header` | post-v0.1.0 | Closed as `not_planned` for v0.1.0; tracked by #59. | No canary deployment/routing manifests found. Current plan says automated canary CD is not critical for v0.1.0. |
| #33 | `[post-v0.1.0] Wire CD for canary + rollback` | post-v0.1.0 | Closed as `not_planned` for v0.1.0; tracked by #59. | CD workflow builds/pushes images only; Helm deploy is commented out and no canary values were found. |
| #34 | `[v0.1.0] Verify Prometheus scrape targets` | partial, v0.1.0 | Keep open; narrow acceptance criteria to API + Envoy unless Payments metrics are added. | ServiceMonitors exist for API and Envoy. Payments has no `/metrics` endpoint and no Payments ServiceMonitor. |
| #35 | `[v0.1.0] Verify Grafana dashboard provisioning` | done | Verified end-to-end on minikube (2026-06-08); close. | All 4 ACs confirmed live: Grafana runs as part of `kube-prometheus-stack` with a randomly generated admin password (Secret `prometheus-grafana`, `ClusterIP`-only, not exposed externally). The dashboard JSON was moved into the chart (`deploy/helm/dashboards/system-overview.json`) and is now provisioned as code via `deploy/helm/templates/grafana-dashboard-system-overview.yaml` — a `ConfigMap` labeled `grafana_dashboard: "1"` that the `grafana-sc-dashboard` sidecar (`k8s-sidecar`, `NAMESPACE=ALL`) auto-loads. `/api/search` confirms "Resilience Lab 0 System Overview" (`uid: adnxcgd`) is now live at `/d/adnxcgd/...`. Also fixed (separate commit, same issue): the "HTTP Status Codes" panel queried the wrong metric (`prometheus_http_requests_total` instead of `http_requests_total{job="resilience-lab-api"}`) — corrected to match the neighboring "Error Rate (%)" panel. |
| #36 | `[v0.1.0] Build Resilience dashboard core panels` | v0.1.0 | Keep open. | Only `system-overview.json` exists. No dedicated `resilience.json` dashboard found. |
| #37 | `[v0.1.0] Add retries, ejections, and 429 panels` | v0.1.0 | Keep open; likely part of dashboard #2. | Envoy metrics and rate-limit metrics exist, but dashboard panels/recording rules for retries/ejections/429 are incomplete or absent. |
| #38 | `[v0.1.0] Deploy Loki + Promtail with rich labels` | v0.1.0 | Keep open. | No Loki/Promtail manifests found. This is now confirmed as part of the v0.1.0 observability MVP. |
| #39 | `[v0.1.0] Add basic Prometheus alert rules` | done | Closed as completed after cluster validation. | Alert rules were added, `/metrics` scrape was fixed, Prometheus showed alert rules healthy/green, and advanced burn-rate scope remains deferred to #59. |
| #40 | `[v0.1.0] Run chaos test: latency injection` | v0.1.0 | Keep open. | Fault injection script supports slow mode; no fresh chaos result document for v0.1.0 found. |
| #41 | `[v0.1.0] Run chaos test: pod kill / partial outage` | v0.1.0 | Keep open. | Fault script supports kill mode; needs current test evidence and runbook notes. |
| #42 | `[v0.1.0] Finalize M3 docs and screenshots` | v0.1.0 | Keep open. | `docs/observability.md` is empty. Runbooks are limited. Existing screenshot covers only system overview. |
| #43 | `[v0.1.0] Review and tighten security baselines` | partial, v0.1.0 | Keep open but narrow to v0.1.0 security review. | Workloads have non-root/read-only/drop caps. No ResourceQuota/LimitRange found; `docs/security.md` is empty. |
| #44 | `[post-v0.1.0] Add network egress control` | post-v0.1.0 | Closed as `not_planned` for v0.1.0; tracked by #59. | Some NetworkPolicies exist, but no comprehensive egress allow-list and verification doc found. |
| #45 | `[post-v0.1.0] Implement runtime security and audit` | post-v0.1.0 | Closed as `not_planned` for v0.1.0; tracked by #59. | No Falco/AuditPolicy manifests found. This is beyond the current MVP recovery scope. |
| #46 | `[v0.1.0] Implement backup and restore scripts for Postgres and Redis` | v0.1.0 | Keep open. | `scripts/pg_backup.sh`, `scripts/redis_backup.sh`, and `docs/backup.md` exist but are empty. No restore scripts found. |
| #47 | `[post-v0.1.0] Verify restore automation in pipeline` | post-v0.1.0 | Closed as `not_planned` for v0.1.0; tracked by #59. | Current MVP needs tested restore, but a GitHub Actions restore-validation pipeline is extra scope. |
| #48 | `[post-v0.1.0] Conduct full chaos test (network + CPU + kill)` | post-v0.1.0 | Closed as `not_planned` for v0.1.0; tracked by #59. | Full combined chaos test is more than the MVP demonstration needs. |
| #49 | `[v0.1.0] Document runbooks and operational SOPs` | v0.1.0 | Keep open. | Runbook index and Prometheus scrape runbook exist. Rollback/outage runbooks requested by the issue are missing. |
| #50 | `[v0.1.0] Polish dashboards and finalize observability` | v0.1.0 | Keep open after #36/#37/#39 are underway. | System dashboard exists, but resilience dashboard, screenshots, and observability docs are incomplete. |
| #51 | `[v0.1.0] Create CHANGELOG and versioning setup` | v0.1.0 | Keep open. | No `CHANGELOG.md` found. |
| #52 | `[v0.1.0] Prepare demo scenario` | v0.1.0 | Keep open. | No `docs/demo-script.md` found. |
| #53 | `[v0.1.0] Perform pre-release validation` | v0.1.0 | Keep open as final validation gate. | This should remain near the end of v0.1.0. |
| #54 | `[v0.1.0] Finalize README and documentation` | v0.1.0 | Keep open. | README exists but still references older milestone status; final docs pass should come after implementation. |
| #55 | `[v0.1.0] Tag and release v0.1.0` | v0.1.0 | Keep open as final release issue. | No release tag action should happen until validation is complete. |
| #56 | `[v0.1.0] Publish postmortem and reflection` | v0.1.0 or immediate post-release | Keep open, but schedule after release validation. | No `docs/postmortem.md` found. |
| #57 | `[v0.1.0] Archive artifacts and clean up` | v0.1.0 final cleanup | Keep open as final cleanup issue. | Should be done after release artifacts and docs settle. |
| #59 | `[post-v0.1.0] Deferred enhancements backlog` | post-v0.1.0 | Keep open as the v0.2.0 candidate umbrella. | Tracks deferred canary, runtime audit, restore pipeline, combined chaos, egress hardening, and advanced burn-rate SLO alerts. |
| #60 | `[v0.1.0 stretch] Add OpenTelemetry tracing baseline` | v0.1.0 stretch | Keep open but do not let it block release if core observability is incomplete. | Minimal tracing baseline: FastAPI/httpx spans, API-to-Payments propagation, OTLP export, and documentation. |

## Recommended GitHub Update Batch

Initial GitHub cleanup has been applied. Remaining follow-up:

1. Keep #34-#38, #50, and #60 as the active observability workstream.
2. Keep #46 and #49 as the M4 operations workstream.
3. Keep #51-#57 as release-prep gates.

## Next Implementation Candidates

Recommended first technical task after issue sync:

1. Verify Prometheus scrape targets (#34).
2. Verify rate-limit metrics and logs (#29).
3. Deploy Loki + Promtail (#38).
4. Add a minimal OpenTelemetry tracing baseline if core logs/metrics are stable (#60).
