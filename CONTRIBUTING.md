# Contributing to Resilience Lab

## 🧭 Branching Workflow

This project follows a **light GitFlow model**:

- `main` → stable, production-ready releases only (tagged)
- `develop` → active development branch (daily work and integration)
- `feature/<name>` → new functionality or task for the current milestone
- `release/<version>` → final polish and testing before tagging a release
- `hotfix/<name>` → quick fix for urgent issues in production

Example:

```

feature/helm-ci
release/v0.1.0
hotfix/missing-envoy-config

```

---

## 🧱 Commit Convention

All commits must follow the `[DAY##]` prefix format:

```

[DAY01] Add initial API service structure
[DAY02] Implement payment processing logic
[DAY15] Add Prometheus metrics integration

```

This keeps progress traceable and aligned with the project timeline.

---

## 🔀 Pull Requests

- **1 PR = 1 logical unit of work** (usually one day or milestone subtask)
- Target branch: `develop`
- Ensure CI checks (lint, test, build) pass before merging
- Self-merge allowed if:
  - CI is ✅ green
  - Code is tested locally
  - README or docs updated when relevant

---

## 🧩 Milestone Overview

| Milestone | Focus                      | Dates    | Goal                                                |
| --------- | -------------------------- | -------- | --------------------------------------------------- |
| **M0**    | Bootstrap                  | 28–31.10 | Repo init, API + Payments + Compose                 |
| **M1**    | Core + CI/CD               | 17–25.11 | Helm deploy, atomic CI/CD, security baseline        |
| **M2**    | Networking & Health        | 26–30.11 | Traefik, Envoy, HPA, PDB, NetPol                    |
| **M3**    | Resilience + Observability | 01–15.12 | Rate-limit, bulkhead, Prometheus, Grafana, Loki     |
| **M4**    | Security + Chaos + Release | 16–31.12 | Backup/restore, chaos tests, polish, release v0.1.0 |

Each milestone has a Definition of Done (DoD) tracked through `[DAY##]` commits and GitHub issues.

---

## 🚀 Release Flow

1. Create `release/<version>` branch from `develop`
2. Finalize docs, CHANGELOG, and version bump
3. Merge to `main` using `--no-ff`
4. Tag the release:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin main --tags
   ```
5. Merge `main` back to `develop` to keep branches in sync

---

## 🧠 Questions

If you're unsure about a change, check the current milestone table above or open a Discussion/Issue for clarification.
