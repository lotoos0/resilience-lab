🧩 Vertical Slice Resilience — Plan v3 (finalny, gotowy do wdrożenia)
🔧 Kluczowe zmiany względem v2

1. Naprawione nakładanie się M3/M4 (Claude miał rację).\
   Uporządkowałem chronologię – teraz masz:
   - M3 (01–15.12) → Resilience + Observability (pełna odporność + widoczność)

   - M4 (16–31.12) → Security, backup, chaos, docs, release polish\
     Całość czytelna, bez datowych kolizji.

2. Włączone najlepsze pomysły z feedbacku:
   - ✅ Fault injection: FAIL_MODE + SLOW_MODE env.

   - ✅ helm test rozszerzony o test API↔Payments (nie tylko /healthz).

   - ✅ dockerfile z security baseline (USER appuser, HEALTHCHECK, no-cache).

   - ✅ PG service w CI (snippet DeepSeeka).

   - ✅ Weekly self-review co sobotę (10:00–10:30) — mini retrospekcja.

   - ✅ Grafana dashboards jako code (obs/dashboards/\*.json).

   - ✅ Makefile target: chaos-latency i k9s.

   - ✅ DoD checklist z dopiskiem „README updated”.

🗂️ Podział Milestone’ów
Milestone Zakres Daty Cel M0 Bootstrap (API + Payments + compose + CI lint/test) 28–31.10 Postawić repo i lokalny dev M1 Core + CI/CD + Security baseline 17–25.11 Helm deploy + atomic CI/CD M2 Networking & Health (Traefik + Envoy + HPA/PDB/NetPol) 26–30.11 Stabilna sieć i odporność L4–L7 M3 Resilience primitives + Observability 01–15.12 Rate-limit, bulkhead, canary + Prometheus, Grafana, Loki M4 Chaos, Security revisit, Backup/Restore, Polish & Release 16–31.12 Finalne testy i release v0.1.0
📋 Definition of Done (aktualizowane)
Wszystkie z v2 + dodatkowe:

- README zaktualizowane po każdym milestone.

- Dashboard JSON-y wersjonowane.

- Fault-inject (make chaos-latency) działa powtarzalnie.

- Weekly retrospekcja w logu projektu (short notes).

📅 Harmonogram — wersja końcowa (day-by-day)
🟠 M0 – Bootstrap (28–31.10)

- 28.10 – Repo init, api + payments, compose (PG+Redis), pytest, lint.

- 29.10 – Dockerfile z security baseline (USER appuser, HEALTHCHECK), Makefile (build/run/lint/test).

- 30.10 – /pay logic, smoke tests, ci-skeleton lint/test.

- 31.10 – Dodaj build do CI, GHCR login, pipeline dry-run.\
  ✅ DoD: docker compose up działa, tests 100%, README seed.

1–16.11: przerwa.
🟡 M1 – Core & CI/CD (17–25.11)

- 17.11 – Helm parent + subcharts, values-dev.yaml, helm install, helm test (API→Payments call).

- 18.11 – CI/CD full: PG service in CI, Trivy fs/image, --atomic, helm diff.

- 19.11 – Integracyjne API↔Payments (z PG), README Quickstart.

- 20.11 – SecurityContext (runAsNonRoot, readOnlyRootFS + /tmp, capDrop, no-priv-esc), probes/resources.

- 21.11 – Make targets: helm-up-dev, helm-test, rollback-%.

- 22.11 – CI polish (cache, badges), README update.

- 23.11 – BUFORY Helm debug/k9s.

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

- 09–10.12 – Dashboard „Resilience”: RPS, 2xx/4xx/429, retries, ejections, p95/p99.

- 11.12 – SLO 99.5% + burn-rate alerts.

- 12–13.12 – Chaos tests: delay + pod kill, alert verification.

- 14.12 – BUFORY (fine-tuning dashboard, alert tuning).

- 15.12 – M3 review & DoD check.\
  ✅ DoD: Resilience visible in Grafanie, SLO alerts działają, chaos test nie łamie SLO.

🟣 M4 – Security, Ops & Release (16–31.12)

- 16–17.12 – Security revisit + NetPol final.

- 18–19.12 – Backup/restore PG + Redis + test w osobnym ns.

- 20.12 – Demo recording (429 + ejection + rollback).

- 21.12 – Runbooki (Payments slow / Redis down / Rollback).

- 22–23.12 – Dashboard/alerts polish, README update.

- 24.12 – Readiness review (krótki dzień).

- 25–26.12 – OFF / README final + screenshots.

- 27.12 – CHANGELOG + docs.

- 28–29.12 – Bufor polish / hygiene (make help, values-prod).

- 30.12 – Final cleanup + release prep.

- 31.12 – RELEASE v0.1.0 + post „What I built & learned”\
  ✅ DoD: Backupy przywrócone, alerty stabilne, release + docs public.

⚙️ Stałe narzędzia i workflow

- make chaos-latency → uruchamia scripts/fault-inject.sh

- make k9s → szybki debug

- obs/dashboards/\*.json → wersjonowane panele

- docs/ → zrzuty z Grafany + outputy helm testów

- Commity: [DAY##]

- Weekly health-check (sobota): 15–30 min przeglądu + mikroadaptacja planu

💾 Repo structure (finalne)

```
vertical-slice-resilience/
├── services/
│   ├── api/
│   ├── payments/
│   ├── catalog/        # Dodany w M1
│   └── worker/         # Dodany w M1
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

🧱 Helm skeleton (skrót)

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

✅ Podsumowanie — wersja v3
Kryterium Status Realizm czasu ✔️ (z buforami) Jasność zakresu ✔️ (M3/M4 rozdzielone) Resilience i Observability ✔️ zintegrowane logicznie Security „shift-left” ✔️ od M1 Dokumentacja iteracyjna ✔️ co milestone Automatyzacja testów ✔️ helm test + fault-inject Risk buffers ✔️ 23.11 / 14.12 / 28–29.12 Demo & Release ✔️ 20–31.12"
