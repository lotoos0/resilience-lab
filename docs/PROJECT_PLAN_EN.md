🧩 Vertical Slice Resilience — Plan v3 (final, ready for implementation)
🔧 Key changes from v2

1. Fixed M3/M4 overlap (Claude was right).\
   Organized chronology – now you have:
   - M3 (01–15.12) → Resilience + Observability (full resilience + visibility)

   - M4 (16–31.12) → Security, backup, chaos, docs, release polish\
     Everything clear, no date conflicts.

2. Incorporated best ideas from feedback:
   - ✅ Fault injection: FAIL_MODE + SLOW_MODE env.

   - ✅ helm test extended with API↔Payments test (not just /healthz).

   - ✅ dockerfile with security baseline (USER appuser, HEALTHCHECK, no-cache).

   - ✅ PG service in CI (DeepSeek snippet).

   - ✅ Weekly self-review every Saturday (10:00–10:30) — mini retrospective.

   - ✅ Grafana dashboards as code (obs/dashboards/\*.json).

   - ✅ Makefile target: chaos-latency and k9s.

   - ✅ DoD checklist with "README updated" note.

🗂️ Milestone Division
Milestone Scope Dates Goal M0 Bootstrap (API + Payments + compose + CI lint/test) 28–31.10 Set up repo and local dev M1 Core + CI/CD + Security baseline 17–25.11 Helm deploy + atomic CI/CD M2 Networking & Health (Traefik + Envoy + HPA/PDB/NetPol) 26–30.11 Stable network and L4–L7 resilience M3 Resilience primitives + Observability 01–15.12 Rate-limit, bulkhead, canary + Prometheus, Grafana, Loki M4 Chaos, Security revisit, Backup/Restore, Polish & Release 16–31.12 Final tests and release v0.1.0
📋 Definition of Done (updated)
All from v2 + additional:

- README updated after each milestone.

- Dashboard JSONs versioned.

- Fault-inject (make chaos-latency) works repeatably.

- Weekly retrospective in project log (short notes).

📅 Schedule — final version (day-by-day)
🟠 M0 – Bootstrap (28–31.10)

- 28.10 – Repo init, api + payments, compose (PG+Redis), pytest, lint.

- 29.10 – Dockerfile with security baseline (USER appuser, HEALTHCHECK), Makefile (build/run/lint/test).

- 30.10 – /pay logic, smoke tests, ci-skeleton lint/test.

- 31.10 – Add build to CI, GHCR login, pipeline dry-run.\
  ✅ DoD: docker compose up works, tests 100%, README seed.

1–16.11: break.
🟡 M1 – Core & CI/CD (17–25.11)

- 17.11 – Helm parent + subcharts, values-dev.yaml, helm install, helm test (API→Payments call).

- 18.11 – CI/CD full: PG service in CI, Trivy fs/image, --atomic, helm diff.

- 19.11 – Integration API↔Payments (with PG), README Quickstart.

- 20.11 – SecurityContext (runAsNonRoot, readOnlyRootFS + /tmp, capDrop, no-priv-esc), probes/resources.

- 21.11 – Make targets: helm-up-dev, helm-test, rollback-%.

- 22.11 – CI polish (cache, badges), README update.

- 23.11 – BUFFER Helm debug/k9s.

- 24–25.11 – Review & tidy-up.\
  ✅ DoD: helm test 200, CI/CD green, security active, docs updated.

🟢 M2 – Networking & Health (26–30.11)

- 26.11 – Traefik IngressRoute (self-signed cert).

- 27.11 – Envoy front-proxy (Deployment + routes).

- 28.11 – Envoy policies (retries, timeouts, outlier ejection).

- 29.11 – HPA, PDB, NetPol (allow-list).

- 30.11 – Fault-inject script (FAIL_MODE/SLOW_MODE), docs screenshots.\
  ✅ DoD: Outlier ejection test pass, HPA triggers, no downtime.

🔵 M3 – Resilience + Observability (01–15.12)

- 01.12 – Rate-limit per-tenant (Redis middleware) + rate-test.

- 02.12 – Bulkhead light (Envoy caps + resource limits).

- 03.12 – Canary header (X-Canary: 1) + canary-curl.sh.

- 04.12 – CD path for canary (values-canary.yaml), rollback checklist.

- 05–06.12 – Prometheus + Grafana (kube-prometheus-stack), metrics in code.

- 07–08.12 – Loki + promtail (labels app,route,tenant), obs/dashboards/\*.json.

- 09–10.12 – Dashboard "Resilience": RPS, 2xx/4xx/429, retries, ejections, p95/p99.

- 11.12 – SLO 99.5% + burn-rate alerts.

- 12–13.12 – Chaos tests: delay + pod kill, alert verification.

- 14.12 – BUFFER (fine-tuning dashboard, alert tuning).

- 15.12 – M3 review & DoD check.\
  ✅ DoD: Resilience visible in Grafana, SLO alerts working, chaos test doesn't break SLO.

🟣 M4 – Security, Ops & Release (16–31.12)

- 16–17.12 – Security revisit + NetPol final.

- 18–19.12 – Backup/restore PG + Redis + test in separate ns.

- 20.12 – Demo recording (429 + ejection + rollback).

- 21.12 – Runbooks (Payments slow / Redis down / Rollback).

- 22–23.12 – Dashboard/alerts polish, README update.

- 24.12 – Readiness review (short day).

- 25–26.12 – OFF / README final + screenshots.

- 27.12 – CHANGELOG + docs.

- 28–29.12 – Buffer polish / hygiene (make help, values-prod).

- 30.12 – Final cleanup + release prep.

- 31.12 – RELEASE v0.1.0 + post "What I built & learned"\
  ✅ DoD: Backups restored, alerts stable, release + docs public.

⚙️ Permanent tools and workflow

- make chaos-latency → runs scripts/fault-inject.sh

- make k9s → quick debug

- obs/dashboards/\*.json → versioned panels

- docs/ → screenshots from Grafana + helm test outputs

- Commits: [DAY##]

- Weekly health-check (Saturday): 15–30 min review + micro-adaptation of plan

💾 Repo structure (final)

```
vertical-slice-resilience/
├── services/
│   ├── api/
│   ├── payments/
│   ├── catalog/        # Added in M1
│   └── worker/         # Added in M1
├── deploy/
│   ├── helm/
│   ├── envoy/
│   └── traefik/
├── obs/
│   ├── prometheus/
│   ├── grafana/
│   ├── loki/
│   └── dashboards/
├── scripts/
│   ├── pg_backup.sh
│   ├── redis_backup.sh
│   ├── fault-inject.sh
│   └── fault-cleanup.sh
├── tests/
├── docs/
├── Makefile
└── .github/workflows/
```

🧱 Helm skeleton (excerpt)

```yaml
# charts/resilience-lab/values.yaml
api:
  image: ghcr.io/user/api:latest
  replicas: 2
payments:
  image: ghcr.io/user/payments:latest
envoy:
  config:
    retries: 2
    timeout: 800ms
    outlierDetection:
      consecutive_5xx: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
security:
  runAsNonRoot: true
  readOnlyRootFS: true
  tmpVolume: true
```

✅ Summary — version v3
Criterion Status Time realism ✔️ (with buffers) Scope clarity ✔️ (M3/M4 separated) Resilience and Observability ✔️ logically integrated Security "shift-left" ✔️ from M1 Iterative documentation ✔️ each milestone Test automation ✔️ helm test + fault-inject Risk buffers ✔️ 23.11 / 14.12 / 28–29.12 Demo & Release ✔️ 20–31.12"
