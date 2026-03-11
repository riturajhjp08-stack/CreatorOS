# Phase 0: Production Baseline

This phase establishes the production bar, cleans up repo hygiene, and defines the operational baseline. No feature work should start until these items are done.

## Outcomes

- Clear SLOs, uptime targets, and error budgets.
- Known environment matrix and ownership.
- Secrets and config handling that does not leak into git.
- Baseline operational metrics and risk register.

## Sub‑Phase 0.1: Production Bar

1. Define SLOs for key endpoints.
2. Define target concurrency and p95 latency targets.
3. Define uptime target and acceptable error budget.

## Sub‑Phase 0.2: Environment Strategy

1. Define environments: local, staging, production.
2. Define deployment strategy: manual, CI/CD, or hybrid.
3. Define rollback approach and database migration policy.

## Sub‑Phase 0.3: Repo Hygiene and Secrets

1. Ensure `.gitignore` covers `.env`, local DB files, logs, and virtualenvs.
2. Remove all secrets from tracked files and rotate any leaked keys.
3. Maintain a sanitized `.env` template for onboarding.

## Sub‑Phase 0.4: Baseline Ops Metrics

1. Capture current response times for top endpoints.
2. Capture current error rates and log volume.
3. Capture dependency map for OAuth and AI providers.

## Deliverables

1. Written SLOs and performance targets.
2. Environment matrix with owners and URLs.
3. Sanitized `.env` template with required variables.
4. Risk register with the top 10 production gaps.

## Exit Criteria

1. No secrets are committed to the repo.
2. Production bar is documented and agreed.
3. Baseline metrics are recorded.
