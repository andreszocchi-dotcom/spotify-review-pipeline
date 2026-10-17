# Cost and runtime calculator (100-review pilot)

## Offline replay (default; no API key, no model calls)

```sh
python -m cost.calculator                      # -> cost/report.md, cost/report.json
python -m cost.calculator --rate-multiplier 2  # -> cost/report_x2.md: API subtotal doubles, time unchanged
```

Importing or running the calculator never calls an API. It recomputes everything from:

| File | Contents |
|---|---|
| [`rates.csv`](rates.csv) | Editable dated prices in billing units (per 1,000,000 tokens), with source links. Jev's price is not published, so its rows are blank and reported as **unknown**, never zero. |
| [`usage.csv`](usage.csv) | Billed units per pilot run × stage × model × item, plus attempts and failed attempts; each row names the `pilot_calls.jsonl` rows it sums. |
| [`pilot_calls.jsonl`](pilot_calls.jsonl) | Every attempted call in the cold and warm runs: request ID, role, review IDs, model, settings, phase, outcome, tokens, timing. |
| [`pilot_records.jsonl`](pilot_records.jsonl) | One final record per pilot review ID with the contract's row hash and common labels. |
| [`pilot_measurements.json`](pilot_measurements.json) | Input checksum, the 100 IDs, statuses, cache hits, per-stage and end-to-end wall-clock seconds. |
| [`assumptions.json`](assumptions.json) | Editable full-run scenarios: budget, verify sample size, retry rates, workers, output-token caps, fallback fraction, optional Jev rate or balance reconciliation. |

Formula: `item_cost = billed_units × price_per_unit`, `total = Σ item_cost` over mutually exclusive items
(uncached input, cache read, cache write, output). Per-million prices are divided by 1,000,000 first.
Local compute (the laptop running the orchestrator) is listed separately as unknown.

To price Jev once known: put the rate in `assumptions.json → typesafe_rate_override_usd_per_mtok`, or record
two console balance readings and the tokens used between them in `typesafe_balance_reconciliation`.

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
| Known API spend (Claude) | $0.0343 | $0.0000 |
| Jev usage | 102,887 input + 19,655 output tokens, price unknown | 0 |

Scaling decision: development checkpoints measured 7.6 texts/s at 1 worker, 15.6 at 2 (500 reviews) and
32.5 at 4 (10,000 reviews) with zero failed calls, so the full run used 8 workers with the circuit breaker
and retry limits in place. See [`report.md`](report.md) for the full tables and projections.
