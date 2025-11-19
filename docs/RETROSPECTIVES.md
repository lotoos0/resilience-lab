# 🔄 Retrospectives

Project retrospectives for continuous improvement and learning.

---

## Table of Contents

- [M0 - Bootstrap](#m0---bootstrap)
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

**Last updated**: November 19, 2025
