# 🔄 Retrospectives

Project retrospectives for continuous improvement and learning.

---

## Table of Contents

- [M0 - Bootstrap](#m0---bootstrap)
- [M1 - Core & CI/CD](#m1---core--cicd)
- [Template for Future Milestones](#template-for-future-milestones)

---

## M0 - Bootstrap

**Milestone**: M0 - Bootstrap
**Planned dates**: October 28-31, 2025 (4 days)
**Actual working dates**: October 28-31, November 17-19, 2025 (7 working days)
**Calendar span**: October 28 - November 19, 2025 (22 calendar days, includes 16-day vacation Nov 1-16)
**Status**: ✅ Completed

---

### 📊 Overview

M0 focused on establishing the foundation: repository structure, basic services (API + Payments), Docker Compose setup, CI/CD pipeline, and comprehensive documentation.

**Timeline**:
- **Planned**: 4 working days (Oct 28-31)
- **Actual**: 7 working days (Oct 28-31 + Nov 17-19)
- **Variance**: 1.75x longer than planned (3 extra days)
- **Note**: 16-day vacation (Nov 1-16) between work periods - no work done during this time

**Scope**: Delivered a more robust foundation than initially scoped, particularly in documentation and CI/CD.

---

### ✅ What Went Well

#### 1. **Solid Technical Foundation**
- ✅ **Two working microservices** (API + Payments) with FastAPI
- ✅ **Docker Compose** setup works reliably across platforms
- ✅ **Health checks** implemented properly (Python-based, not curl)
- ✅ **Database + Redis** infrastructure in place
- ✅ **Security baseline** established (non-root containers, health checks)

**Impact**: Strong foundation for M1 work. No technical debt.

#### 2. **Comprehensive CI/CD Pipeline**
- ✅ **GitHub Actions** with 5 jobs: lint, test, integration-test, build, build-and-push
- ✅ **Automated testing** (unit + integration separated)
- ✅ **Docker image publishing** to GHCR
- ✅ **Pip caching** for faster builds
- ✅ **Multi-branch support** (main, develop, test/**, feature/**)

**Impact**: Every push is validated. CI catches issues early.

#### 3. **Excellent Documentation**
- ✅ **README.md** - Comprehensive (560+ lines)
- ✅ **ARCHITECTURE.md** - System design with ADRs (469 lines)
- ✅ **DEVELOPMENT.md** - Developer guide (664 lines)
- ✅ **DEPLOYMENT.md** - Deployment procedures (662 lines)
- ✅ **CONTRIBUTING.md** - Contribution guidelines (698 lines)
- ✅ **CODE_OF_CONDUCT.md** - Community standards (180 lines)

**Impact**: New contributors can onboard quickly. Future-me will thank current-me.

#### 4. **Testing Infrastructure**
- ✅ **Pytest** setup with markers (unit vs integration)
- ✅ **Integration tests** with actual service calls
- ✅ **Virtual environment** workflow for local dev
- ✅ **Makefile** with helpful targets

**Impact**: Tests run reliably in CI and locally.

#### 5. **Learning and Problem-Solving**
- ✅ Solved **PEP 668** issues on Arch Linux (venv approach)
- ✅ Fixed **Pydantic validation** errors (type hints)
- ✅ Debugged **healthcheck** configuration (Python vs curl)
- ✅ Mastered **pytest markers** for test separation
- ✅ Learned **GitHub Actions** caching and optimization

**Impact**: Real-world debugging experience. Better understanding of tooling.

---

### 🔧 What Could Be Improved

#### 1. **Timeline Estimation**
- ⚠️ **Planned**: 4 working days
- ⚠️ **Actual**: 7 working days
- ⚠️ **Variance**: 1.75x longer than estimated (3 extra days)

**Root causes**:
- Scope expanded during execution (documentation grew organically from basic README to 6 comprehensive docs)
- Learning curve for some tools (GitHub Actions, pytest markers, venv workflow)
- Debugging took more time than anticipated (4 CI iterations for docker-compose syntax)
- Comprehensive documentation wasn't in original scope

**Lesson**: 1.75x variance is reasonable for a bootstrap milestone with learning curve. Factor in documentation and debugging time for future estimates.

**Action for M1**:
- Add 1.5-2x buffer for new features
- Add 20% buffer for debugging
- Separate "core MVP" from "enhancements" upfront
- Track scope changes as they happen

#### 2. **Scope Creep**
- 📈 **Documentation expanded** beyond initial plan
  - Started with basic README
  - Ended with 6 comprehensive docs (3000+ lines total)
- 📈 **Testing became more sophisticated** than M0 required
  - Added pytest markers
  - Separated unit/integration
  - Added venv workflow

**Impact**: Better quality, but slower delivery.

**Lesson**: Scope creep isn't always bad if it adds value, but needs to be acknowledged.

**Action for M1**:
- Define clear "Definition of Done" upfront
- Separate MVP from enhancements
- Track scope changes explicitly

#### 3. **Iterative Debugging Process**
- 🔄 **CI pipeline** required 4+ iterations to fix `docker compose` command
- 🔄 **Health checks** went through 3 iterations (curl → Python → config removal)
- 🔄 **Requirements** needed multiple updates (requests, pydantic version)

**Root cause**: Trial-and-error approach instead of researching first.

**Lesson**: Quick research upfront saves iteration time.

**Action for M1**:
- Check documentation before implementing
- Test locally before pushing to CI
- Use `act` or similar tools for local CI testing

#### 4. **Platform-Specific Issues**
- ⚠️ **Arch Linux PEP 668** caused pip install failures
- ⚠️ **Python 3.13** compatibility required pydantic update
- ⚠️ **GitHub Actions** uses different docker-compose syntax

**Lesson**: Platform differences are real. Plan for them.

**Action for M1**:
- Document platform-specific requirements
- Test on multiple environments if possible
- Use containerized workflows to minimize platform variance

#### 5. **Commit Message Consistency**
- ⚠️ Some commits followed `[DAY##]` format, others didn't
- ⚠️ Commit messages varied in detail

**Lesson**: Discipline in commit messages needs improvement.

**Action for M1**:
- Use git hooks to enforce commit format
- Create commit message template
- Review commits before pushing

---

### 📚 Lessons Learned

#### Technical Lessons

1. **Virtual environments are essential on Arch Linux**
   - PEP 668 prevents system Python modification
   - Venv approach works reliably
   - Document in setup instructions

2. **Health checks: Python > curl**
   - Containers don't need curl if Python available
   - Python-based health checks are more flexible
   - Reduces image size

3. **GitHub Actions syntax differs from local docker-compose**
   - `docker compose` (space) in CI
   - `docker-compose` (hyphen) locally
   - Always test CI changes in CI environment

4. **Pytest markers are powerful**
   - Separate fast unit tests from slow integration tests
   - Enables faster feedback loop
   - CI can run tests in parallel

5. **Documentation is an investment**
   - Takes time upfront
   - Saves time in the long run
   - Helps clarify architecture decisions

#### Process Lessons

1. **Estimates should include buffer for learning**
   - 1.5-2x for new tools and patterns
   - 1.2-1.5x for familiar tools
   - 20% for unexpected issues and debugging
   - M0's 1.75x variance (7 vs 4 days) was reasonable given learning curve

2. **Scope creep isn't always bad**
   - M0 documentation is exceptional (far beyond initial plan)
   - Will save significant time in M1-M4
   - But track scope changes explicitly
   - 3 extra days for better documentation was good investment

3. **Debugging time is significant**
   - CI debugging took ~4 iterations (docker compose syntax)
   - Local debugging can prevent CI failures
   - Research before implementing saves iteration time

4. **Platform testing matters**
   - Arch Linux has different constraints (PEP 668)
   - GitHub Actions has different environment (docker compose vs docker-compose)
   - Test on target platform early

5. **Iteration is learning**
   - Every failed CI run taught something
   - Every bug fixed improved understanding
   - Document learnings for future reference
   - Accept that first time with new tools takes longer

#### Personal Lessons

1. **Perfectionism vs Progress**
   - Documentation could be "good enough" instead of "perfect"
   - Balance quality with velocity
   - Know when to ship

2. **Learning takes time**
   - First time with pytest markers
   - First time with GitHub Actions caching
   - First time with virtual env workflow
   - This is okay and expected

3. **Documentation as thinking**
   - Writing docs clarified architecture
   - ADRs helped justify decisions
   - Process of documenting revealed gaps

---

### 📈 Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Duration (working days)** | 4 days | 7 days | ⚠️ 1.75x over |
| **Calendar span** | 4 days | 22 days (incl. 16-day vacation) | ℹ️ Expected |
| **Services** | 2 (API + Payments) | 2 | ✅ Met |
| **CI Pipeline** | Basic | Comprehensive (5 jobs) | ✅ Exceeded |
| **Tests** | Basic | Unit + Integration | ✅ Exceeded |
| **Documentation** | README | 6 comprehensive docs | ✅ Exceeded |
| **Code Coverage** | 80% | Not measured yet | ⚠️ Pending |
| **Security Baseline** | Basic | Non-root, healthchecks | ✅ Met |

**Overall**: Delivered significantly more than planned (especially documentation and CI/CD) with reasonable time variance (1.75x).

---

### 🎯 Action Items for M1

Based on M0 learnings, here's what to do differently in M1:

#### Planning & Estimation
- [ ] **Add 1.5-2x time buffer** for features with learning curve
- [ ] **Add 20% buffer** for debugging and unexpected issues
- [ ] **Define clear DoD** before starting tasks
- [ ] **Separate MVP from enhancements** in planning
- [ ] **Track scope changes** explicitly during milestone

#### Process Improvements
- [ ] **Research before implementing** (check docs, examples)
- [ ] **Test locally before CI push** to catch issues early
- [ ] **Use git hooks** to enforce commit message format
- [ ] **Create commit message template** in `.gitmessage`

#### Technical Improvements
- [ ] **Measure code coverage** and track over time
- [ ] **Set up local CI testing** with `act` or similar
- [ ] **Document platform-specific requirements** upfront
- [ ] **Create troubleshooting guide** from M0 issues

#### Documentation
- [ ] **Update docs incrementally** instead of big-bang at end
- [ ] **Keep RETROSPECTIVES.md** updated throughout milestone
- [ ] **Document decisions** as they're made (ADRs)

---

### 🏆 Key Achievements

Despite taking longer than planned, M0 delivered significant value:

1. **Production-ready foundation** - Not just a prototype
2. **Comprehensive documentation** - Rare in early-stage projects
3. **Robust CI/CD** - Catches issues automatically
4. **Security baseline** - Built-in from day one
5. **Testing infrastructure** - Ready for TDD in M1
6. **Platform compatibility** - Works on Linux, macOS, Windows (WSL2)

**Verdict**: M0 took 1.75x longer than planned (7 days vs 4 days), but delivered 3x more value than initially scoped. The extra 3 days invested in comprehensive documentation, robust CI/CD, and testing infrastructure will pay dividends in M1-M4.

---

### 💭 Final Thoughts

**What I'm proud of**:
- Documentation quality is exceptional (6 comprehensive docs, 3000+ lines)
- CI/CD pipeline is production-grade (5 jobs, caching, multi-branch)
- Architecture is well thought out (ADRs, clear patterns)
- No shortcuts taken on security (non-root containers from day one)
- Testing infrastructure ready for TDD in next milestones

**What I'd do differently**:
- Define "MVP vs enhancements" upfront to track scope changes
- Research-first approach instead of trial-and-error (especially for CI)
- Document platform-specific quirks earlier (Arch Linux PEP 668)
- Test CI changes locally before pushing

**What went better than expected**:
- Time variance was only 1.75x (3 extra days) - reasonable for bootstrap with learning curve
- Documentation became a strength instead of an afterthought
- Platform compatibility issues caught and solved early
- CI/CD more comprehensive than originally planned

**Looking ahead to M1**:
- Apply lessons learned (1.5-2x buffer for new features)
- Focus on Helm charts and K8s deployment
- Keep documentation momentum going
- Measure and track code coverage

**Overall**: M0 was a solid success. Took 3 extra working days (plus 16-day vacation in between), but delivered a production-ready foundation with exceptional documentation. The 1.75x time variance is well within acceptable range for a bootstrap milestone with significant learning involved. Ready for M1 with confidence.

---

## M1 - Core & CI/CD

**Milestone**: M1 - Core & CI/CD
**Planned dates**: November 17-25, 2025 (9 days)
**Actual working dates**: November 17-26, 2025 (10 days)
**Calendar span**: November 17-26, 2025 (10 calendar days)
**Status**: ✅ Completed

---

### 📊 Overview

M1 focused on production-grade Kubernetes deployment: Helm charts with subcharts, enhanced security baseline (SecurityContext, probes, resources), CI/CD improvements (Trivy scanning, PostgreSQL service), and comprehensive Kubernetes documentation.

**Timeline**:
- **Planned**: 9 working days (Nov 17-25)
- **Actual**: 10 working days (Nov 17-26)
- **Variance**: 1.11x longer than planned (1 extra day)

**Scope**: Delivered all core M1 objectives plus additional security hardening beyond initial scope.

---

### ✅ What Went Well

#### 1. **Production-Ready Helm Charts**
- ✅ **Parent chart + subcharts** architecture (api, payments)
- ✅ **Values structure** with dev/prod overrides (values.yaml, values-dev.yaml)
- ✅ **Chart dependencies** managed via Chart.lock
- ✅ **Templates** with helpers, deployment, service, tests
- ✅ **Helm lint** passes without errors

**Impact**: Kubernetes deployment is fully functional and follows best practices.

#### 2. **Enhanced Security Baseline**
- ✅ **SecurityContext** at pod and container level
  - `runAsNonRoot: true`
  - `runAsUser: 1000`
  - `fsGroup: 1000`
  - `readOnlyRootFilesystem: true`
  - `allowPrivilegeEscalation: false`
  - `capabilities.drop: ["ALL"]`
- ✅ **Temporary filesystem** with emptyDir volumes for /tmp
- ✅ **CVE remediation** (CVE-2024-47874, CVE-2025-62727)
- ✅ **Dependency updates** (Starlette 0.41.3, FastAPI 110.0)

**Impact**: Production-grade security from day one. Passes security audits.

#### 3. **Comprehensive Health Probes**
- ✅ **startupProbe** for slow-starting applications
- ✅ **livenessProbe** for pod restart on failure
- ✅ **readinessProbe** for traffic routing
- ✅ **Resource limits and requests** properly configured

**Impact**: Kubernetes can properly manage pod lifecycle and resource allocation.

#### 4. **CI/CD Improvements**
- ✅ **Trivy scanning** (filesystem + Docker images)
- ✅ **PostgreSQL service** in CI pipeline
- ✅ **Pip caching** for faster builds
- ✅ **Trivy version upgrade** (v2 → v3)
- ✅ **SARIF upload** to GitHub Security tab

**Impact**: Security vulnerabilities caught automatically. CI runs faster with caching.

#### 5. **Enhanced Makefile**
- ✅ **helm-deps** - Build Helm dependencies
- ✅ **helm-lint** - Lint Helm charts
- ✅ **helm-up-dev** - Install with dev values
- ✅ **helm-test** - Run Helm tests
- ✅ **helm-down** - Uninstall release
- ✅ **rollback-%** - Rollback to specific revision

**Impact**: Developer experience significantly improved. One-command deployments.

#### 6. **Kubernetes Documentation**
- ✅ **README** extended with full Kubernetes section (300+ lines)
- ✅ **Prerequisites** (kubectl, Helm, k3d/minikube/kind)
- ✅ **Installation instructions** (step-by-step)
- ✅ **Testing procedures** (port-forward, curl tests)
- ✅ **Troubleshooting guide** (common issues)

**Impact**: Anyone can deploy to Kubernetes following the documentation.

---

### 🔧 What Could Be Improved

#### 1. **Security CVE Remediation Process**
- ⚠️ **DAY06 had 6 commits** fixing CVE-2024-47874 and build errors
- ⚠️ **FastAPI/Starlette compatibility** issues during updates
- ⚠️ **Iterative debugging** of dependency conflicts

**Root causes**:
- Starlette version bump broke FastAPI compatibility
- Multiple attempts to find working version combination
- Did not test dependency updates locally before pushing to CI

**Lesson**: Dependency updates need local testing before CI push.

**Action for M2**:
- Use `pip-compile` or similar for dependency locking
- Test dependency updates in isolated environment
- Check changelogs before major version bumps
- Run full test suite locally before pushing

#### 2. **Trivy Deprecation**
- ⚠️ **Trivy v2 → v3 migration** required mid-milestone
- ⚠️ **GitHub Action syntax changed** between versions

**Root cause**: Used deprecated version from documentation/examples.

**Lesson**: Always check for latest stable versions.

**Action for M2**:
- Pin specific versions in CI (e.g., `@v3` not `@master`)
- Subscribe to security tool release notes
- Review CI dependencies quarterly

#### 3. **Git Tag Missing**
- ⚠️ **v0.1.0-M1 tag** not created during milestone
- ⚠️ **Retrospective** delayed until after milestone end

**Root cause**: Focused on implementation, forgot release formalities.

**Lesson**: Include tag creation in Definition of Done.

**Action for M2**:
- Add "Create git tag" to DoD checklist
- Write retrospective during milestone (not after)
- Use GitHub releases for better visibility

#### 4. **Timeline Variance (Minor)**
- ⚠️ **Planned**: 9 days (Nov 17-25)
- ⚠️ **Actual**: 10 days (Nov 17-26)
- ⚠️ **Variance**: 1.11x (1 extra day)

**Root cause**: Security CVE fixes took longer than expected (DAY06).

**Lesson**: Security fixes can be unpredictable. Buffer needed.

**Action for M2**:
- Add 20% buffer for security/dependency work
- Plan "security day" for proactive CVE scanning
- Use Dependabot for automated dependency PRs

---

### 📚 Lessons Learned

#### Technical Lessons

1. **Helm chart structure matters**
   - Parent chart + subcharts pattern scales well
   - Values inheritance reduces duplication
   - _helpers.tpl makes templates DRY

2. **SecurityContext is multi-layered**
   - Pod-level: runAsNonRoot, runAsUser, fsGroup
   - Container-level: readOnlyRootFilesystem, allowPrivilegeEscalation, capabilities
   - Both levels needed for full security

3. **readOnlyRootFilesystem requires planning**
   - Applications need writable /tmp
   - Use emptyDir volumes for temporary storage
   - Plan for logs, cache, temp files

4. **Health probes serve different purposes**
   - startupProbe: Gives slow apps time to start
   - livenessProbe: Restarts broken pods
   - readinessProbe: Controls traffic routing

5. **Dependency updates are risky**
   - FastAPI and Starlette versions must be compatible
   - Test locally before pushing to CI
   - Read changelogs for breaking changes

6. **Trivy is powerful but evolving**
   - Catches CVEs automatically
   - v2 → v3 had breaking changes
   - SARIF output integrates with GitHub Security

#### Process Lessons

1. **1.11x variance is excellent**
   - M1 took only 1 extra day (10 vs 9 planned)
   - Much better than M0's 1.75x
   - Security fixes were the main variance cause

2. **CVE remediation is unpredictable**
   - Can't always predict dependency conflicts
   - Need buffer time for security work
   - Worth doing proactively vs reactively

3. **Definition of Done prevents forgotten tasks**
   - Git tag and retrospective were afterthoughts
   - Should be in DoD from start
   - Checklist prevents omissions

4. **Documentation during implementation works**
   - Updated README as features were added
   - Less work at milestone end
   - More accurate documentation

---

### 📈 Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Duration (working days)** | 9 days | 10 days | ⚠️ 1.11x over |
| **Helm charts** | Parent + 2 subcharts | ✅ Delivered | ✅ Met |
| **SecurityContext** | Basic | Full (8 settings) | ✅ Exceeded |
| **Health probes** | liveness + readiness | +startup probe | ✅ Exceeded |
| **CI/CD security** | Trivy scan | Trivy + CVE fixes | ✅ Exceeded |
| **Makefile targets** | 5 targets | 6 targets | ✅ Exceeded |
| **README** | Helm section | 300+ lines K8s docs | ✅ Exceeded |
| **Git tag** | v0.1.0-M1 | Not created (pending) | ⚠️ Delayed |
| **CVE count** | Unknown | 2 fixed (CVE-2024-47874, CVE-2025-62727) | ✅ Proactive |

**Overall**: Delivered all core objectives plus enhanced security beyond scope, with minimal time variance (1.11x).

---

### 🎯 Action Items for M2

Based on M1 learnings, here's what to do differently in M2:

#### Planning & Estimation
- [x] **1.5-2x time buffer worked** - Continue for new features
- [ ] **Add 20% security buffer** for dependency/CVE work
- [ ] **Include git tag in DoD** from start
- [ ] **Plan "security day"** for proactive CVE scanning

#### Process Improvements
- [ ] **Test dependency updates locally** before CI push
- [ ] **Use pip-compile** for dependency locking
- [ ] **Write retrospective during milestone** (not after)
- [ ] **Set up Dependabot** for automated dependency PRs

#### Technical Improvements
- [ ] **Pin CI tool versions** (@v3 not @master)
- [ ] **Document CVE remediation process** in runbooks
- [ ] **Create dependency update checklist** (test, changelog, compatibility)
- [ ] **Subscribe to security tool release notes**

#### Documentation
- [x] **Incremental doc updates worked well** - Continue
- [ ] **Add "Release Process" section** to CONTRIBUTING.md
- [ ] **Document dependency management** strategy

---

### 🏆 Key Achievements

M1 delivered production-ready Kubernetes deployment with exceptional security:

1. **Production-grade Helm charts** - Parent + subcharts architecture
2. **Enhanced security baseline** - 8 SecurityContext settings, CVE fixes
3. **Comprehensive health probes** - startup + liveness + readiness
4. **Improved CI/CD** - Trivy scanning, PostgreSQL service, caching
5. **Enhanced DX** - 6 Makefile targets for one-command operations
6. **Excellent documentation** - 300+ lines of Kubernetes deployment guide

**Verdict**: M1 took only 1 extra day (10 vs 9 planned, 1.11x variance), delivered all core objectives, and exceeded scope with enhanced security. The time spent on CVE remediation (DAY06) was unpredictable but valuable. Overall: excellent execution.

---

### 💭 Final Thoughts

**What I'm proud of**:
- **1.11x variance** - Only 1 extra day! Much better than M0's 1.75x
- **Security-first approach** - Full SecurityContext, proactive CVE fixes
- **Production-ready** - Not just "works", but "production-grade"
- **Enhanced DX** - Makefile targets make Kubernetes deployment trivial
- **Comprehensive docs** - 300+ lines of K8s documentation

**What I'd do differently**:
- **Test dependency updates locally** - Would have saved 5 commits on DAY06
- **Create git tag during milestone** - Not as an afterthought
- **Write retrospective incrementally** - Daily notes → final doc
- **Pin Trivy version from start** - Avoid v2 → v3 migration

**What went better than expected**:
- **Time variance only 1.11x** - Excellent estimation improvement from M0
- **Security exceeded scope** - Full SecurityContext + CVE fixes
- **Documentation momentum** - Kept updating docs during implementation
- **CI/CD maturity** - Trivy + caching + PostgreSQL service

**Unexpected challenges**:
- **DAY06 CVE remediation** - 6 commits for FastAPI/Starlette compatibility
- **Trivy v2 deprecation** - Had to migrate mid-milestone
- **readOnlyRootFilesystem** - Needed emptyDir for /tmp (learned this)

**Looking ahead to M2**:
- **Focus**: Traefik ingress, Envoy service mesh, HPA, PDB, NetworkPolicy
- **Apply M1 lessons**: Security buffer, dependency testing, incremental retro
- **Build on M1 foundation**: Production-ready K8s with advanced networking
- **Continue momentum**: 1.11x variance target, security-first approach

**Overall**: M1 was a strong success. Took 1 extra day (1.11x variance - excellent improvement from M0's 1.75x), delivered all core objectives plus enhanced security beyond scope. The CVE remediation work (DAY06) was unpredictable but valuable. Production-ready Kubernetes deployment with exceptional security baseline. Ready for M2 (Networking) with confidence.

---

## Template for Future Milestones

Use this template for M1-M4 retrospectives:

```markdown
## M# - [Milestone Name]

**Milestone**: M# - [Name]
**Planned dates**: [Start] - [End]
**Actual dates**: [Actual Start] - [Actual End]
**Status**: [In Progress / Completed / Blocked]

### 📊 Overview
Brief summary of milestone goals and outcomes.

### ✅ What Went Well
- Achievement 1
- Achievement 2
- Achievement 3

### 🔧 What Could Be Improved
- Issue 1 (root cause, lesson, action)
- Issue 2 (root cause, lesson, action)
- Issue 3 (root cause, lesson, action)

### 📚 Lessons Learned
Key learnings from this milestone.

### 📈 Metrics
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Duration | X days | Y days | Status |
| Feature 1 | Target | Actual | Status |

### 🎯 Action Items for Next Milestone
- [ ] Action 1
- [ ] Action 2
- [ ] Action 3

### 💭 Final Thoughts
Overall reflection on the milestone.
```

---

**Last updated**: November 26, 2025
