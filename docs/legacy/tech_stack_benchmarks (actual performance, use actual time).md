# ResKiosk Tech Stack Benchmarks (Actual Time)

Measured on: 2026-03-02 (Asia/Manila)  
Method: local benchmark script using FastAPI `TestClient`, direct runtime calls for formatter/rewriter, 127.0.0.1 Ollama.

## API Endpoint Latency

Runs: 10 per endpoint

| Endpoint | Avg | P95 | Min | Max |
|---|---:|---:|---:|---:|
| `GET /admin/ping` | 1.19 ms | 1.68 ms | 0.87 ms | 2.18 ms |
| `GET /kb/snapshot` | 7.13 ms | 7.99 ms | 5.96 ms | 9.28 ms |
| `GET /emergency/active` | 2.32 ms | 2.55 ms | 1.86 ms | 4.00 ms |

## Query Path Benchmark

Runs: 5 sample `/query` requests

| Metric | Value |
|---|---:|
| Average total `/query` time | 2093.40 ms |
| P95 total `/query` time | 2096.80 ms |
| Minimum total `/query` time | 2083.35 ms |
| Maximum total `/query` time | 2110.16 ms |

Observed internal retrieval stage in logs during same run: ~19 ms to ~27 ms (semantic search is fast; answer formatting path dominates total).

## Rewriter Benchmark

Config:
- `RESKIOSK_QUERY_REWRITE=true`
- `RESKIOSK_REWRITE_MODEL=llama3.2:3b`

Runs: 5

| Metric | Value |
|---|---:|
| Average rewrite time | 4175.51 ms |
| Minimum rewrite time | 2984.50 ms |
| Maximum rewrite time | 8850.90 ms |

## Formatter Benchmark

### Formatter with `llama3.2:3b`
Config:
- `RESKIOSK_FORMAT_MODEL=llama3.2:3b`

Runs: 3

| Metric | Value |
|---|---:|
| Average format time | 7233.06 ms |
| Minimum format time | 5095.35 ms |
| Maximum format time | 11072.63 ms |

### Formatter with `translategemma:4b` (not installed at test time)
Config:
- `RESKIOSK_FORMAT_MODEL=translategemma:4b`

Runs: 3

| Metric | Value |
|---|---:|
| Average call time | 2050.35 ms |
| Minimum call time | 2043.58 ms |
| Maximum call time | 2055.86 ms |

Note: this timing reflects fallback behavior after Ollama 404 (`model 'translategemma:4b' not found`), returning raw KB text rather than true model generation.

## Benchmark Context / Caveats

- These are single-machine local measurements on a development setup.
- Results are sensitive to:
  - model loaded state / warmup
  - concurrent requests
  - whether model is actually installed and available
  - CPU contention from kiosk, hub, and console running together
- For production-like numbers, re-run after ensuring:
  - `translategemma:4b` is installed
  - no background load spikes
  - repeated warm and cold runs are captured separately.

