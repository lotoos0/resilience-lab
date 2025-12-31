# 📋 TODO - January 2026 (Refactoring Plan)

**Created:** Dec 31, 2025
**Start:** Jan 1, 2026
**Target:** Release v0.1.0 by Jan 22, 2026

**📌 Source:** `docs/REFACTORING_PLAN_2026.md`

---

## 🔥 WEEK 1: M3 Completion (Jan 1-7, 2026)

### Day 1-2 (Jan 1-2) - Resilience Patterns Completion

#### [M3-001] Rate Limiting Load Testing
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Install k6 load testing tool
- [ ] Write k6 script: `tests/load/rate-limit-test.js`
  - Test under limit (50 req/min)
  - Test over limit (100 req/min → expect 429)
- [ ] Run load test against API
- [ ] Verify metrics in `/metrics` endpoint
- [ ] Document results in `docs/M3_RESILIENCE_PATTERNS.md`

**Acceptance:**
- k6 test shows 429 responses when exceeding 60 req/min
- `rl_denied_total` counter increments
- Logs show structured tenant info

**Commits:** 2-3

---

#### [M3-002] Bulkhead Validation + Metrics
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Write k6 load test: `tests/load/bulkhead-test.js`
  - Scenario 1: 80 concurrent connections (under limit)
  - Scenario 2: 150 concurrent connections (over limit → expect 503)
- [ ] Port-forward Envoy: `kubectl port-forward svc/envoy-proxy 8080:10000`
- [ ] Run bulkhead test
- [ ] Check Envoy stats: `/stats | grep upstream_cx`
- [ ] Validate metrics show connection pool saturation
- [ ] Document in `docs/resilience/bulkhead.md`

**Acceptance:**
- Under limit: ~90% success rate
- Over limit: 503 errors, circuit opens
- Envoy metrics show `upstream_cx_overflow`

**Commits:** 2-3

---

#### [M3-003] Retry/Timeout Tuning
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Update `deploy/envoy/envoy-config.yaml`:
  - `num_retries: 2`
  - `per_try_timeout: 0.2s` (200ms)
  - `retry_on: "5xx,reset,connect-failure"`
- [ ] Apply ConfigMap update
- [ ] Restart Envoy proxy
- [ ] Test retry behavior (inject 5xx → verify retries)
- [ ] Document retry policy

**Acceptance:**
- Retry policy active (2 retries, 200ms each)
- Latency impact < 500ms (p95)
- No retry storms

**Commits:** 1-2

---

#### [M3-004] Circuit Breaker Outlier Detection
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Update `deploy/envoy/envoy-config.yaml` with outlier detection:
  ```yaml
  outlier_detection:
    consecutive_5xx: 5
    interval: 10s
    base_ejection_time: 30s
    max_ejection_percent: 50
  ```
- [ ] Create fault injection script: `scripts/inject-5xx.sh`
- [ ] Test outlier detection (inject errors → verify ejection)
- [ ] Document in `docs/resilience/circuit-breaker.md`

**Acceptance:**
- 5 consecutive 5xx → host ejected for 30s
- Envoy logs show ejection events
- Metrics exposed to Prometheus

**Commits:** 2-3

---

### Day 3-4 (Jan 3-4) - Prometheus + Grafana

#### [M3-005] Deploy Prometheus Stack
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Add Helm repo: `helm repo add prometheus-community ...`
- [ ] Create `deploy/prometheus/values.yaml`
- [ ] Deploy kube-prometheus-stack
- [ ] Verify pods running: `kubectl get pods -n monitoring`
- [ ] Port-forward Prometheus UI

**Acceptance:**
- Prometheus UI accessible
- All targets UP (API, Envoy, Redis, Nodes)
- Metrics scraping successfully

**Commits:** 2-3

---

#### [M3-006] Configure ServiceMonitors + Recording Rules
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create ServiceMonitor for API
- [ ] Create ServiceMonitor for Envoy
- [ ] Create recording rules: `deploy/prometheus/rules.yaml`
- [ ] Apply PrometheusRule CRD
- [ ] Verify rules in Prometheus UI

**Acceptance:**
- All ServiceMonitors active
- Recording rules visible in Prometheus
- Metrics queryable via PromQL

**Commits:** 2-3

---

#### [M3-007] Deploy Grafana + System Overview Dashboard
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Port-forward Grafana
- [ ] Create Dashboard #1: "System Overview"
  - Request rate (req/s) by service
  - Error rate (%) - 2xx/4xx/5xx breakdown
  - P50, P95, P99 latency
  - Pod status
- [ ] Export dashboard JSON: `deploy/grafana/dashboards/system-overview.json`
- [ ] Commit dashboard to git

**Acceptance:**
- Grafana accessible
- System Overview dashboard shows real-time data
- Dashboard JSON in git

**Commits:** 2-3

---

#### [M3-008] Basic Alert Rules
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create alert rules: `deploy/prometheus/alerts.yaml`
- [ ] Apply PrometheusRule
- [ ] Test alert firing (inject errors → verify alert)
- [ ] Document alerts in `docs/observability/alerts.md`

**Acceptance:**
- 2 basic alerts configured
- Test alert fires successfully

**Commits:** 1-2

---

### Day 5 (Jan 5) - Canary Deployment (Simplified)

#### [M3-009] Manual Canary Deployment Setup
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create `deploy/helm/values-canary.yaml`
- [ ] Update Envoy config with weighted clusters
- [ ] Create canary testing script: `scripts/canary-test.sh`
- [ ] Test canary deployment manually
- [ ] Document process in `docs/deployment/canary.md`

**Acceptance:**
- Canary deployment successful
- Traffic split working (90/10, 50/50)
- Rollback tested
- Manual runbook created

**Note:** Automated CD pipeline SKIPPED for MVP

**Commits:** 3-4

---

### Day 6-7 (Jan 6-7) - Loki + SLO

#### [M3-010] Deploy Loki + Promtail
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Add Grafana Helm repo
- [ ] Create `deploy/loki/values.yaml`
- [ ] Deploy Loki stack with Promtail
- [ ] Verify logs flowing
- [ ] Add Loki datasource to Grafana
- [ ] Test LogQL queries

**Acceptance:**
- Loki aggregating logs from all pods
- Grafana Explore shows logs
- LogQL queries working
- Retention active (7 days)

**Commits:** 2-3

---

#### [M3-011] SLO Definition + Basic Alert
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Define SLOs in `docs/observability/slo.md`:
  - Availability SLO: 99.5%
  - Latency SLO: p95 < 500ms
- [ ] Create SLO tracking recording rule
- [ ] Create burn-rate alert
- [ ] Add SLO panel to Grafana dashboard

**Acceptance:**
- SLO defined and documented
- Recording rule active
- Burn-rate alert working
- SLO visible in Grafana

**Commits:** 2-3

---

## ✅ M3 CHECKLIST (End of Week 1)

- [ ] [M3-001] Rate limiting load tested ✅
- [ ] [M3-002] Bulkhead validated ✅
- [ ] [M3-003] Retry/timeout tuned ✅
- [ ] [M3-004] Outlier detection active ✅
- [ ] [M3-005] Prometheus deployed ✅
- [ ] [M3-006] ServiceMonitors + recording rules ✅
- [ ] [M3-007] Grafana + System Overview dashboard ✅
- [ ] [M3-008] Basic alerts configured ✅
- [ ] [M3-009] Canary deployment working (manual) ✅
- [ ] [M3-010] Loki + Promtail deployed ✅
- [ ] [M3-011] SLO defined + burn-rate alert ✅

**M3 Progress: 100% (MVP version)**

---

## 🔥 WEEK 2: M4 Security + Ops (Jan 8-14, 2026)

### Day 8-9 (Jan 8-9) - Security Revisit

#### [M4-001] Security Audit
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Run Trivy scan on all images
- [ ] Fix HIGH/CRITICAL vulnerabilities
- [ ] Run kube-bench on cluster
- [ ] Create security audit report: `docs/security/audit-2026-01.md`

**Acceptance:**
- 0 HIGH/CRITICAL vulnerabilities
- kube-bench score >80%

**Commits:** 3-4

---

#### [M4-002] NetworkPolicy Final Review
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Review existing NetworkPolicies
- [ ] Test deny-all + allow-list
- [ ] Update policies if needed
- [ ] Document network topology

**Acceptance:**
- NetworkPolicies tested and working
- Zero-trust network model enforced

**Commits:** 1-2

---

#### [M4-003] Secrets Management
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Install SealedSecrets
- [ ] Encrypt existing secrets (PostgreSQL, Redis passwords)
- [ ] Create sealed secrets: `deploy/secrets/sealed-secret-*.yaml`
- [ ] Test secret decryption
- [ ] Document in `docs/security/secrets.md`

**Acceptance:**
- All secrets encrypted at rest
- SealedSecrets working
- No plaintext secrets in git

**Commits:** 2-3

---

### Day 10-11 (Jan 10-11) - Backup & Restore

#### [M4-004] PostgreSQL Backup Script
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create backup script: `scripts/pg_backup.sh`
- [ ] Create CronJob for scheduled backups
- [ ] Test backup manually
- [ ] Store backups in PVC

**Acceptance:**
- Backup script working
- CronJob scheduled (daily at 2 AM)
- Backups stored securely

**Commits:** 2-3

---

#### [M4-005] Redis Backup Script
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create backup script: `scripts/redis_backup.sh`
- [ ] Create CronJob
- [ ] Test backup

**Acceptance:**
- Redis RDB snapshots created
- CronJob scheduled

**Commits:** 1-2

---

#### [M4-006] Restore Testing
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create test namespace: `resilience-lab-restore-test`
- [ ] Restore PostgreSQL backup
- [ ] Restore Redis backup
- [ ] Verify data integrity
- [ ] Measure restore time (target: <15 min)
- [ ] Create runbook: `docs/runbooks/disaster-recovery.md`

**Acceptance:**
- Restore successful
- Data verified
- Restore time <15 min
- Runbook complete

**Commits:** 2-3

---

### Day 12 (Jan 12) - Chaos Testing (Manual)

#### [M4-007] Manual Chaos Tests
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create chaos testing script: `scripts/chaos-test.sh`
- [ ] Test 1: Pod deletion
- [ ] Test 2: Network latency injection
- [ ] Test 3: High CPU load
- [ ] Document results in `docs/chaos/chaos-test-results.md`
- [ ] Create chaos testing runbook

**Acceptance:**
- 3 chaos scenarios tested
- System resilience validated
- Alerts triggered correctly
- Recovery automatic

**Commits:** 2-3

---

### Day 13-14 (Jan 13-14) - Dashboard Polish + Docs

#### [M4-008] Grafana Resilience Dashboard
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create Dashboard #2: "Resilience Patterns"
  - Rate limiting metrics
  - Circuit breaker status
  - Bulkhead utilization
  - Retry metrics
- [ ] Export dashboard: `deploy/grafana/dashboards/resilience-patterns.json`

**Acceptance:**
- 2nd dashboard deployed
- All resilience metrics visible
- Dashboard JSON in git

**Commits:** 2-3

---

#### [M4-009] README Comprehensive Update
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Update `README.md` with:
  - Project overview + goals
  - Architecture diagram (Mermaid)
  - Quick start guide
  - Resilience patterns implemented
  - Observability stack
  - Security features
  - Deployment instructions
  - Links to runbooks
- [ ] Add CI/CD badges
- [ ] Proofread and polish

**Acceptance:**
- README comprehensive (>500 lines)
- Screenshots included
- Architecture diagram clear

**Commits:** 2-3

---

#### [M4-010] Architecture Diagram
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create architecture diagram (Mermaid)
- [ ] Add to README.md and `docs/ARCHITECTURE.md`

**Acceptance:**
- Diagram shows all components
- Traffic flow clear
- Resilience patterns highlighted

**Commits:** 1-2

---

#### [M4-011] Runbooks Finalization
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Finalize 4 runbooks in `docs/runbooks/`:
  1. Payments slow response
  2. Redis down recovery
  3. Rollback procedure
  4. Security incident response

**Acceptance:**
- 4 runbooks complete
- Step-by-step instructions
- Tested procedures

**Commits:** 2-3

---

## ✅ M4 CHECKLIST (End of Week 2)

- [ ] [M4-001] Security audit passed ✅
- [ ] [M4-002] NetworkPolicy finalized ✅
- [ ] [M4-003] Secrets encrypted ✅
- [ ] [M4-004] PostgreSQL backups automated ✅
- [ ] [M4-005] Redis backups automated ✅
- [ ] [M4-006] Restore tested successfully ✅
- [ ] [M4-007] Chaos tests passed (3 scenarios) ✅
- [ ] [M4-008] Resilience dashboard deployed ✅
- [ ] [M4-009] README comprehensive ✅
- [ ] [M4-010] Architecture diagram created ✅
- [ ] [M4-011] 4 runbooks finalized ✅

**M4 Progress: 100%**

---

## 🔥 WEEK 3: Polish & Release (Jan 15-22, 2026)

### Day 15-16 (Jan 15-16) - Demo & Final Docs

#### [RELEASE-001] Demo Materials
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Choose demo format (video or screenshots)
- [ ] Demo scenarios:
  1. Normal operation (Grafana dashboard)
  2. Rate limiting in action (429 responses)
  3. Circuit breaker ejection (pod failure)
  4. Canary deployment (traffic shift)
  5. Chaos test (pod deletion recovery)
- [ ] Create demo materials
- [ ] Upload to `docs/demo/`

**Commits:** 1-2

---

#### [RELEASE-002] CHANGELOG.md
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create `CHANGELOG.md` with all milestones
- [ ] Add commit links for major features

**Commits:** 1

---

#### [RELEASE-003] Release Notes Draft
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create release notes: `docs/RELEASE_NOTES_v0.1.0.md`
- [ ] Prepare for GitHub Release

**Commits:** 1

---

### Day 17-18 (Jan 17-18) - Final Polish

#### [RELEASE-004] Code Cleanup
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Remove TODOs from code
- [ ] Remove commented code
- [ ] Fix linting errors
- [ ] Format code
- [ ] Run full test suite

**Commits:** 2-3

---

#### [RELEASE-005] CI/CD Optimization
**Priority:** P2 - Medium | **Status:** ⬜ TODO

**Tasks:**
- [ ] Add GitHub Actions caching
- [ ] Parallelize jobs where possible
- [ ] Target: Pipeline <5 min

**Commits:** 1-2

---

#### [RELEASE-006] Makefile Enhancement
**Priority:** P2 - Medium | **Status:** ⬜ TODO

**Tasks:**
- [ ] Update `Makefile` with helpful targets
- [ ] Add `make help` command
- [ ] Test all targets

**Commits:** 1-2

---

#### [RELEASE-007] Production Values
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create `deploy/helm/values-prod.yaml`
- [ ] Document production deployment

**Commits:** 1-2

---

### Day 19-20 (Jan 19-20) - Pre-Release Review

#### [RELEASE-008] DoD Checklist Review
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Review Definition of Done from `PROJECT_PLAN_PL.md`
- [ ] Create checklist: `docs/DOD_FINAL_REVIEW.md`
- [ ] Mark all items complete

**Commits:** 1

---

#### [RELEASE-009] Documentation Proofreading
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Proofread all docs
- [ ] Fix typos, grammar
- [ ] Verify all links work

**Commits:** 1-2

---

#### [RELEASE-010] Final Security Scan
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Run final Trivy scan
- [ ] Run kube-bench
- [ ] Check for exposed secrets
- [ ] Create final security report

**Commits:** 1

---

#### [RELEASE-011] Performance Baseline
**Priority:** P2 - Medium | **Status:** ⬜ TODO

**Tasks:**
- [ ] Run performance tests (k6)
- [ ] Document baseline in `docs/PERFORMANCE_BASELINE.md`

**Commits:** 1-2

---

### Day 21-22 (Jan 21-22) - RELEASE v0.1.0 🚀

#### [RELEASE-012] Git Tag & GitHub Release
**Priority:** P0 - Critical | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create git tag: `v0.1.0`
- [ ] Build and push final Docker images
- [ ] Create GitHub Release

**Commits:** 1

---

#### [RELEASE-013] Release Announcement
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Write blog post
- [ ] Post on LinkedIn
- [ ] Share on Twitter/X
- [ ] Update portfolio

**Commits:** N/A

---

#### [RELEASE-014] Project Retrospective
**Priority:** P1 - High | **Status:** ⬜ TODO

**Tasks:**
- [ ] Create final retrospective in `docs/RETROSPECTIVES.md`

**Commits:** 1

---

## ✅ RELEASE CHECKLIST (End of Week 3)

- [ ] [RELEASE-001] Demo materials created ✅
- [ ] [RELEASE-002] CHANGELOG.md complete ✅
- [ ] [RELEASE-003] Release notes drafted ✅
- [ ] [RELEASE-004] Code cleaned up ✅
- [ ] [RELEASE-005] CI/CD optimized ✅
- [ ] [RELEASE-006] Makefile enhanced ✅
- [ ] [RELEASE-007] Production values ready ✅
- [ ] [RELEASE-008] DoD 100% satisfied ✅
- [ ] [RELEASE-009] Documentation proofread ✅
- [ ] [RELEASE-010] Security scan clean ✅
- [ ] [RELEASE-011] Performance baseline documented ✅
- [ ] [RELEASE-012] GitHub Release published ✅
- [ ] [RELEASE-013] Release announced ✅
- [ ] [RELEASE-014] Retrospective complete ✅

**RELEASE Progress: 100%**

---

## 🎯 SUMMARY

**Total Tasks:** 36 (11 M3 + 11 M4 + 14 Release)

**Timeline:**
- Week 1 (Jan 1-7): M3 Completion (11 tasks)
- Week 2 (Jan 8-14): M4 Security + Ops (11 tasks)
- Week 3 (Jan 15-22): Polish + Release (14 tasks)

**Expected Commits:** 60-80 atomic commits (3-4 per day)

**Final Deliverable:** Release v0.1.0 on Jan 22, 2026 🎉

---

**Legend:**
- ⬜ TODO - Not started
- 🔄 IN PROGRESS - Currently working
- ✅ DONE - Completed

**Priority Levels:**
- P0 - Critical (must complete)
- P1 - High (should complete)
- P2 - Medium (nice to have)

---

**Last updated:** Dec 31, 2025
**Author:** DevOps Team
**Start:** Jan 1, 2026
**Target:** Jan 22, 2026
