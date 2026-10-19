# Cost and runtime calculator (100-review pilot)

## Offline replay (default; no API key, no model calls)

```sh
python -m cost.calculator                      # -> cost/report.md, cost/report.json
python -m cost.calculator --rate-multiplier 2  # -> cost/report_x2.md: API subtotal doubles, time unchanged
```

Importing or running the calculator never calls an API. It recomputes everything from:

| File | Contents |
|---|---|
| [`rates.csv`](rates.csv) | Editable dated prices in billing units (per 1,000,000 tokens), with source links. Jev's rate ($0.042 / 1M input, output free) is not in its public docs; it was read from the TypeSafe console on 2026-10-19. Before that reading the calculator reported Jev cost as **unknown**, never zero. |
| [`typesafe_console_usage.csv`](typesafe_console_usage.csv) | Hourly usage exported from the TypeSafe console (key ID and email columns removed), for reconciliation. |
| [`usage.csv`](usage.csv) | Billed units per pilot run × stage × model × item, plus attempts and failed attempts; each row names the `pilot_calls.jsonl` rows it sums. |
| [`pilot_calls.jsonl`](pilot_calls.jsonl) | Every attempted call in the cold and warm runs: request ID, role, review IDs, model, settings, phase, outcome, tokens, timing. |
| [`pilot_records.jsonl`](pilot_records.jsonl) | One final record per pilot review ID with the contract's row hash and common labels. |
| [`pilot_measurements.json`](pilot_measurements.json) | Input checksum, the 100 IDs, statuses, cache hits, per-stage and end-to-end wall-clock seconds. |
| [`assumptions.json`](assumptions.json) | Editable full-run scenarios: budget, verify sample size, retry rates, workers, output-token caps, fallback fraction, optional Jev rate or balance reconciliation. |

Formula: `item_cost = billed_units × price_per_unit`, `total = Σ item_cost` over mutually exclusive items
(uncached input, cache read, cache write, output). Per-million prices are divided by 1,000,000 first.
Local compute (the laptop running the orchestrator) is listed separately as unknown.

### Jev reconciliation (2026-10-19)

| | Pipeline call logs (all runs) | TypeSafe console (7 days) |
|---|---|---|
| Requests | 493,725 | 493,319 |
| Tokens (input + output) | 533.0M + 97.1M = 630.0M | 629.5M |
| Spend at $0.042 / 1M input | **$22.38** | **$22.37** (console estimate) |

The console notes its stats may be delayed; the ~0.5M-token gap matches the recorded demo run made minutes before
the reading. Recorded in `assumptions.json → typesafe_console_reconciliation`.

**Budget outcome:** the full run's Jev cost was **$21.96** (522.7M input tokens), above the $20 Jev budget. The run
started before Jev's rate was known (it is not published, and the console balance lags); spend passed the $20
prepaid credit and the owner's auto-recharge topped the balance up. The calculator's projection from the 10k
checkpoint ($21.90) would have flagged this had the rate been known in advance; the lesson is to obtain the rate
from the provider console *before* scaling, not after. Claude spend for the full run was $0.135.

## Explicit paid pilot (spends real credit)

```sh
python -m cost.pilot --confirm-paid
```

Verifies `cost_100.csv` against `data/manifest.json`, deletes the pilot database (empty result cache),
runs the full pipeline with one worker (enrich → verify 20% sample → group → rank → memo), then runs it again
on the saved state. Without `--confirm-paid` it refuses and exits.

## Measured results (2026-10-16)

| | Cold | Warm |
|---|---|---|
| Wall clock | 44.5 s | 0.12 s |
| Enrichment calls | 100 (0 failed) | **0** (100 result-cache hits) |
| Verify / group / memo calls | 1 / 7 / 1 | 0 / 0 / 0 (cached artifacts) |
| API spend | $0.0386 = Claude $0.0343 + Jev $0.0043 | $0.0000 |
| Jev usage | 102,887 input + 19,655 output tokens (output is free) | 0 |

Scaling decision: development checkpoints measured 7.6 texts/s at 1 worker, 15.6 at 2 (500 reviews) and
32.5 at 4 (10,000 reviews) with zero failed calls, so the full run used 8 workers with the circuit breaker
and retry limits in place. See [`report.md`](report.md) for the full tables and projections.
