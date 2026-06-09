# Release Notes Template

Use this schema for every release. Keep the tone consistent: technical but human.

---

## Schema

```markdown
# vX.Y.Z-MN — <short tagline: what this release is about>

## Overview

<2-4 sentences, casual and direct. Talk to the reader like a person.
Explain WHY this release exists — what problem it solves or what state the project is in.
Do NOT just list features here. Save that for the sections below.
Example openers: "Hey folks!", "This one's been cooking for a while —", "Quick one today —">

---

## What's New

- **<Feature name>** — one sentence explaining what it does and why it matters.
- **<Feature name>** — ...

## Improvements

- <What changed and why it's better now.>
- ...

## Bug Fixes

- Fixed <what was broken and what the symptom was>.
- ...

## Breaking Changes

- <Describe exactly what breaks and how to migrate.>
- None. ← use this if nothing breaks

## Upgrade Notes

- <Concrete steps needed after pulling this version: rebuild, migrate, check config, etc.>
- <Be specific — file names, commands, flags.>
```

---

## Rules

- **Overview is human.** No bullet points, no headers inside it. Write like you're talking to the team.
- **What's New = net-new functionality.** If it didn't exist before, it goes here.
- **Improvements = existing things that got better.** Perf, reliability, DX, test coverage.
- **Bug Fixes = things that were broken.** Name the symptom, not just the fix.
- **Breaking Changes = honest.** If something breaks on upgrade, say so clearly. Don't bury it.
- **Upgrade Notes = actionable.** Steps someone can follow without reading the diff.

---

## Example (v0.1.1-M3)

```markdown
# v0.1.1-M3 — Observability & Logging Complete

## Overview

Hey folks! 👋

This one's been cooking for a while — v0.1.1-M3 is the release that actually *finishes* what M3 promised.
The previous tag landed with the skeleton in place, but the full observability stack wasn't quite there yet. Now it is.

No new features were added for the sake of adding them. This is a focused pass: get the logs flowing,
get the dashboards showing real data, get the rate limiter backed by something real, and fix the rough edges
that were slowing down debugging.

---

## What's New

- **Loki + Promtail** — centralized log aggregation deployed and wired into the stack. Query logs from Grafana via LogQL.
- **Tenant context in logs** — every API log line now includes tenant metadata.
- **Redis** — deployed as the backing store for the rate-limit middleware.
- **Grafana: Traffic & Latency dashboard** — request rates, latency percentiles, error rates per endpoint.
- **Grafana: System Overview dashboard** — CPU, memory, pod health.

## Improvements

- Rate-limit k6 smoke tests now target the correct endpoint and validate actual limiting behavior.
- Codecov patch coverage fixed — `main.py` is now covered.
- Grafana HTTP status codes panel query corrected.

## Bug Fixes

- Fixed incorrect Grafana query for HTTP status code breakdown panel.
- Fixed rate-limit smoke test targeting an excluded endpoint (was always green for the wrong reason).

## Breaking Changes

- None.

## Upgrade Notes

- Re-run `helm upgrade` to pick up Redis and the Loki/Promtail stack.
- Two new Grafana dashboards are provisioned automatically — no manual import needed.
- Check `values.yaml` for the new Redis section if you had custom rate-limit config.
```
