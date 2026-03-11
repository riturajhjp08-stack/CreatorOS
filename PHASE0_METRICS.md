# Phase 0 Metrics Baseline

Record a baseline for the current code before any production changes.

## What to record

1. Date/time of measurement and environment (local/staging).
2. p95 latency for:
   - `GET /health`
   - `POST /api/auth/login`
   - `GET /api/analytics/dashboard`
3. Error rate at low load (1 RPS) and moderate load (20 RPS).
4. CPU, memory, and DB connection stats during tests.

## Suggested tools

- `hey` or `wrk` for load tests.
- `curl` for single-call latency checks.

## Example commands

```bash
curl -s -w "\\n%{time_total}\\n" http://127.0.0.1:5000/health
hey -n 1000 -c 20 http://127.0.0.1:5000/health
```

## Results

Fill in:

```
Environment:
Date:

/health p95:
/api/auth/login p95:
/api/analytics/dashboard p95:

Error rate @ 1 RPS:
Error rate @ 20 RPS:

CPU:
Memory:
DB:
```
