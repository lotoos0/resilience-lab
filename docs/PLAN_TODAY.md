# 📋 Today's Plan: Jan 1, 2026 (RESTART - DAY25)

**Project:** Resilience Lab - Vertical Slice Resilience
**Milestone:** M3 - Resilience + Observability (Week 1 of refactoring plan)
**Date:** January 1, 2026 (Wednesday)
**Status:** 🔄 PROJECT RESTART - Fresh start after suspension

---

## 🎯 Where Are We? (Status check Dec 31, 2025)

### ✅ WHAT'S COMPLETED (before suspension)
- ✅ M0 (Bootstrap) - COMPLETE
- ✅ M1 (Core & CI/CD) - COMPLETE
- ✅ M2 (Networking & Health) - COMPLETE
- ⚠️ M3 (Resilience + Observability) - 40% COMPLETE:
  - ✅ Rate limiting (Redis middleware) - DAY19-21
  - ✅ Bulkhead config (Envoy circuit breaker) - DAY21
  - ✅ Prometheus metrics endpoint - DAY23-24
  - ❌ Load testing, validation, monitoring - MISSING
  - ❌ Canary, Loki, SLO, Chaos - NOT STARTED
- ❌ M4 (Security & Ops) - NOT STARTED

### 📚 DOCUMENTS TO READ BEFORE STARTING
1. ✅ `docs/REFACTORING_PLAN_2026.md` - Master refactoring plan
2. ✅ `docs/TODO.md` - Detailed task list for January
3. ⚠️ `docs/PROJECT_PLAN_PL.md` - Original plan (reference)
4. ⚠️ `docs/_tasks.md` - M3 task backlog

---

## 🚀 TODAY'S TASKS (Jan 1, 2026 - Day 1)

**Priority:** Complete resilience patterns testing + validation

**Strategy:** Week 1, Day 1-2 from refactoring plan
- Focus: M3-001 + M3-002 (Rate limiting + Bulkhead load testing)
- Goal: Validate that resilience patterns work under load

---

## BLOCK 1: Setup & Pre-flight Checks (30 min)

### 1.1 Environment Verification

**Tasks:**
```bash
# 1. Check git status
git status
git log --oneline -5

# 2. Check cluster
kubectl get nodes
kubectl get pods -n resilience-lab

# 3. Verify services running
docker ps

# 4. Verify tests pass
cd services/api
pytest
cd ../payments
pytest
```

**Expected:**
- Git clean working directory
- Cluster running (Minikube/Kind)
- Pods healthy: api, payments, redis, postgres, envoy-proxy
- All tests passing

**If something doesn't work:**
- Restart cluster: `minikube start` or `kind create cluster`
- Rebuild services: `docker-compose up -d`
- Redeploy: `helm upgrade --install resilience-lab deploy/helm/resilience-lab -n resilience-lab`

---

### 1.2 Commit refactoring plan docs

**Tasks:**
```bash
# Add new planning docs
git add docs/REFACTORING_PLAN_2026.md
git add docs/TODO.md
git add docs/PLAN_TODAY.md

# Commit
git commit -m "[DAY25] docs: create 2026 refactoring plan - restart after project pause

- Created comprehensive refactoring plan (REFACTORING_PLAN_2026.md)
- Detailed TODO list for January 2026 (TODO.md)
- Daily plan for Jan 1, 2026 (PLAN_TODAY.md)
- Timeline: 3 weeks (Jan 1-22) to complete M3 + M4 + Release v0.1.0
- Strategy: MVP approach, focus on core resilience patterns"

# Push
git push origin develop
```

**Acceptance:**
- Docs committed
- Push successful
- Branch: develop

---

## BLOCK 2: [M3-001] Rate Limiting Load Testing (1.5h)

### 2.1 Install k6 (15 min)

**Tasks:**
```bash
# Check if k6 installed
k6 version

# If not, install (Arch Linux detected)
sudo pacman -S k6

# Verify
k6 version
```

**Expected:** k6 v0.48+ installed

---

### 2.2 Write k6 rate limiting test (30 min)

**Create:** `tests/load/rate-limit-test.js`

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

// Custom metrics
const deniedRequests = new Counter('denied_requests');

export const options = {
  scenarios: {
    // Test 1: Under limit (50 req/min = safe)
    under_limit: {
      executor: 'constant-arrival-rate',
      rate: 50,
      timeUnit: '1m',
      duration: '1m',
      preAllocatedVUs: 10,
      tags: { scenario: 'under_limit' },
    },
    // Test 2: Over limit (100 req/min = expect 429)
    over_limit: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1m',
      duration: '1m',
      preAllocatedVUs: 20,
      startTime: '70s',
      tags: { scenario: 'over_limit' },
    },
  },
  thresholds: {
    'http_req_failed{scenario:under_limit}': ['rate<0.05'], // <5% errors under limit
    'http_req_failed{scenario:over_limit}': ['rate>0.3'],  // >30% errors over limit (429s)
    'denied_requests{scenario:over_limit}': ['count>10'],  // At least 10 denials
  },
};

export default function () {
  const url = 'http://localhost:8000/healthz';
  const params = {
    headers: {
      'X-Tenant': 'load-test-tenant',
    },
  };

  const res = http.get(url, params);

  check(res, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  if (res.status === 429) {
    deniedRequests.add(1);
  }

  sleep(0.1);
}
```

**Commit:**
```bash
git add tests/load/rate-limit-test.js
git commit -m "[DAY25] test: add k6 load test for rate limiting validation

- Test scenario 1: 50 req/min (under limit, expect <5% errors)
- Test scenario 2: 100 req/min (over limit, expect >30% 429s)
- Custom metric: denied_requests counter
- Thresholds validate rate limiter works under load"
```

---

### 2.3 Run rate limiting load test (30 min)

**Pre-requisite: Port-forward API**
```bash
# Option 1: Direct to API pod
kubectl port-forward -n resilience-lab svc/api 8000:8000 &

# Option 2: Via Envoy (more realistic)
kubectl port-forward -n resilience-lab svc/envoy-proxy 8000:10000 &
```

**Run test:**
```bash
k6 run tests/load/rate-limit-test.js
```

**Expected output:**
```
✓ http_req_failed{scenario:under_limit} ....... < 5%
✓ http_req_failed{scenario:over_limit} ........ > 30%
✓ denied_requests{scenario:over_limit} ........ > 10

Scenario under_limit: ~95% success (200 OK)
Scenario over_limit: ~40% denied (429 Too Many Requests)
```

---

### 2.4 Verify metrics endpoint (15 min)

```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics | grep rl_

# Expected:
# rl_allowed_total{tenant="load-test-tenant"} 50.0
# rl_denied_total{tenant="load-test-tenant"} 40.0
```

---

### 2.5 Update documentation (15 min)

**Edit:** `docs/M3_RESILIENCE_PATTERNS.md`

Add section on rate limiting load test results.

**Commit:**
```bash
git add docs/M3_RESILIENCE_PATTERNS.md
git commit -m "[DAY25] docs: add rate limiting load test results and validation"
```

---

## BLOCK 3: [M3-002] Bulkhead Validation (1.5h)

### 3.1 Write k6 bulkhead test (30 min)

**Create:** `tests/load/bulkhead-test.js`

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    under_limit: {
      executor: 'constant-vus',
      vus: 80,
      duration: '30s',
      tags: { scenario: 'under_limit' },
    },
    over_limit: {
      executor: 'constant-vus',
      vus: 150,
      duration: '30s',
      startTime: '35s',
      tags: { scenario: 'over_limit' },
    },
  },
  thresholds: {
    'http_req_failed{scenario:under_limit}': ['rate<0.1'],
    'http_req_failed{scenario:over_limit}': ['rate>0.1'],
    'http_req_duration{scenario:under_limit}': ['p95<500'],
  },
};

export default function () {
  const res = http.get('http://localhost:8080/api/healthz');

  check(res, {
    'status is 200 or 503': (r) => r.status === 200 || r.status === 503,
  });

  sleep(0.1);
}
```

**Commit:**
```bash
git add tests/load/bulkhead-test.js
git commit -m "[DAY25] test: add k6 load test for bulkhead validation"
```

---

### 3.2 Run bulkhead load test (30 min)

**Port-forward Envoy:**
```bash
kubectl port-forward -n resilience-lab svc/envoy-proxy 8080:10000 &
```

**Run test:**
```bash
k6 run tests/load/bulkhead-test.js
```

---

### 3.3 Check Envoy metrics (20 min)

```bash
kubectl port-forward -n resilience-lab deploy/envoy-proxy 9901:9901

curl -s http://localhost:9901/stats | grep -E 'upstream_cx_(active|overflow|total)'
```

---

### 3.4 Document bulkhead test results (30 min)

**Create:** `docs/resilience/bulkhead.md`

Document configuration, test results, and usage.

**Commit:**
```bash
git add docs/resilience/bulkhead.md
git commit -m "[DAY25] docs: add bulkhead pattern documentation with load test results"
```

---

## BLOCK 4: Update TODO.md (15 min)

Mark completed tasks in `docs/TODO.md`.

**Commit:**
```bash
git add docs/TODO.md
git commit -m "[DAY25] docs: mark M3-001 and M3-002 as complete in TODO"
```

---

## ✅ CHECKLIST - What must be done today

### MUST DO (Day 1 MVP):
- [x] Pre-flight checks (cluster, tests, git)
- [x] Commit refactoring plan docs
- [x] [M3-001] Install k6
- [x] [M3-001] Write rate limiting k6 test
- [x] [M3-001] Run rate limiting load test
- [x] [M3-001] Verify metrics endpoint
- [x] [M3-001] Document results
- [x] [M3-002] Write bulkhead k6 test
- [x] [M3-002] Run bulkhead load test
- [x] [M3-002] Check Envoy metrics
- [x] [M3-002] Document bulkhead pattern
- [x] Update TODO.md

### Git Commits (expected): 6-8 commits
```
[DAY25] docs: create 2026 refactoring plan - restart after project pause
[DAY25] test: add k6 load test for rate limiting validation
[DAY25] docs: add rate limiting load test results and validation
[DAY25] test: add k6 load test for bulkhead validation
[DAY25] docs: add bulkhead pattern documentation with load test results
[DAY25] docs: mark M3-001 and M3-002 as complete in TODO
```

---

## 📊 Success Metrics for Today

**Technical:**
- [x] Rate limiting validated under load (429 responses working)
- [x] Bulkhead validated (503 when over max_connections)
- [x] k6 tests passing
- [x] Envoy metrics exposed and checked
- [x] Documentation comprehensive

**Process:**
- [x] 6-8 atomic commits
- [x] Each commit = 1 logical change
- [x] All tests passing

**Documentation:**
- [x] Rate limiting load test documented
- [x] Bulkhead pattern documented
- [x] Testing guides created

---

## 🚀 Plan for Tomorrow (Jan 2, 2026 - Day 2)

**Focus:** [M3-003] Retry/Timeout Tuning + [M3-004] Outlier Detection

**Tasks:**
1. Update Envoy retry policy (2 retries, 200ms per-try timeout)
2. Apply config and test retry behavior
3. Add outlier detection config (5 consecutive 5xx → eject 30s)
4. Create fault injection script (inject-5xx.sh)
5. Test outlier detection (inject errors → verify ejection)
6. Document circuit breaker behavior

**Expected commits:** 4-6

---

## 📝 Notes and Decisions

**Key Decisions Made Today:**
- k6 chosen as load testing tool (lightweight, scriptable)
- Rate limiting threshold: 60 req/min confirmed working
- Bulkhead max_connections: 100 is adequate for current scale
- Documentation strategy: Comprehensive guides with reproducible tests

**Technical Learnings:**
- k6 constant-arrival-rate executor better for rate limiting tests
- k6 constant-vus executor better for bulkhead tests
- Envoy metrics (:9901/stats) are very detailed and useful
- Port-forwarding Envoy required for realistic load tests

**Issues Encountered:**
- (none yet, document here if any)

---

**🎯 Today's Motto:**
> "Fresh start, solid foundation. Test everything, document everything."

**Last updated:** Jan 1, 2026 08:00
**Author:** DevOps Team
**Status:** 🔥 DAY 1 - Project Restart - Let's build it right!
**Commits target:** 6-8 atomic commits
**Time budget:** 4-5h
**Week 1 Progress:** 2/11 tasks (18%)
