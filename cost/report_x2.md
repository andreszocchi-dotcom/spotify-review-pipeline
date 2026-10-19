# 100-review pilot: cost and runtime calculator

Generated offline by `python -m cost.calculator` from saved evidence; no API calls.
Rate multiplier: 2.0

## Pilot input

- File `data/cost_100.csv` · SHA-256 `c884ac3b9be5066995d5063f96ad9af6e5e082975788c1684c4f6b6ea661dd0e`
- Rows 100 · distinct nonempty texts 100 · statuses {'completed': 100}
- Limits: {'jev_token_cap': 250000, 'usd_cap': 0.5, 'workers': 1, 'verify_rate': 0.2, 'verify_max': 20}

## Rates (editable: `cost/rates.csv`)

| model:item | quoted | checked | source |
|---|---|---|---|
| claude-haiku-5-5:input_tokens | 0.10 USD per 1,000,000 tokens | 2026-10-16 | https://platform.claude.com/docs/en/about-claude/pricing |
| claude-haiku-5-5:cache_read_input_tokens | 0.01 USD per 1,000,000 tokens | 2026-10-16 | https://platform.claude.com/docs/en/about-claude/pricing |
| claude-haiku-5-5:cache_creation_input_tokens | 0.125 USD per 1,000,000 tokens | 2026-10-16 | https://platform.claude.com/docs/en/about-claude/pricing |
| claude-haiku-5-5:output_tokens | 0.50 USD per 1,000,000 tokens | 2026-10-16 | https://platform.claude.com/docs/en/about-claude/pricing |
| claude-sonnet-5-5:input_tokens | 2.00 USD per 1,000,000 tokens | 2026-10-16 | https://platform.claude.com/docs/en/about-claude/pricing |
| claude-sonnet-5-5:output_tokens | 10.00 USD per 1,000,000 tokens | 2026-10-16 | https://platform.claude.com/docs/en/about-claude/pricing |
| jev-1.13.0:input_tokens | 0.042 USD per 1,000,000 tokens | 2026-10-19 | https://console.typesafe.ai (Usage page: 'Estimated at $0.042/MTok input - Free output'; not on public docs) |
| jev-1.13.0:output_tokens | 0 USD per 1,000,000 tokens | 2026-10-19 | https://console.typesafe.ai (Usage page: 'Estimated at $0.042/MTok input - Free output'; not on public docs) |

## Measured cold run

- End-to-end wall clock **44.511 s** · throughput 2.25 rows/s
- Stage seconds: {'ingest': 0.205, 'enrich': 13.251, 'verify': 6.414, 'group': 10.406, 'rank': 0.006, 'memo': 13.996}
- Result-cache hits: 0 · enrichment calls: 100
- Known API spend **$0.0773**
- Known cost per 1,000 rows $0.7729 · per completed record $0.000773

| stage | provider | model | attempts | failed | input | cache read | cache write | output | cost |
|---|---|---|---|---|---|---|---|---|---|
| enrich | typesafe | jev-1.13.0 | 100 | 0 | 102,887 | 0 | 0 | 19,655 | $0.0086 |
| group | anthropic | claude-haiku-5-5 | 7 | 0 | 5,486 | 0 | 0 | 721 | $0.0018 |
| memo | anthropic | claude-sonnet-5-5 | 1 | 0 | 6,078 | 0 | 0 | 2,078 | $0.0659 |
| verify | anthropic | claude-haiku-5-5 | 1 | 0 | 2,044 | 0 | 0 | 547 | $0.0010 |

## Measured warm run

- End-to-end wall clock **0.122 s** · throughput 819.67 rows/s
- Stage seconds: {'ingest': 0.031, 'enrich': 0.007, 'verify': 0.004, 'group': 0.004, 'rank': 0.004, 'memo': 0.002}
- Result-cache hits: 100 · enrichment calls: 0
- Known API spend **$0.0000**
- Known cost per 1,000 rows $0.0000 · per completed record $0.000000

| stage | provider | model | attempts | failed | input | cache read | cache write | output | cost |
|---|---|---|---|---|---|---|---|---|---|
| (no model calls) | | | 0 | 0 | 0 | 0 | 0 | 0 | $0.0000 |

## Full-run projection

Measured enrichment: {'input_tokens': 1028.9, 'output_tokens': 196.6} tokens per distinct text; 7.55 texts/s with 1 worker.
Full run: 660,622 rows · 660,609 nonempty · 13 empty-text quarantines · 484,189 distinct texts.

### base reuse (484,189 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 503,149,212 | 96,119,021 | $42.26 |
| verify | claude-haiku-5-5 | 107,310 | 28,718 | $0.05 |
| group | claude-haiku-5-5 | 6,583 | 865 | $0.00 |
| memo | claude-sonnet-5-5 | 6,382 | 2,182 | $0.07 |

- Known API cost by provider: {'typesafe': 42.26, 'anthropic': 0.12}
- Unknown-cost providers: none
- Enrichment time (modeled, 8 workers): **2.81 h**
- ⚠ OVER BUDGET: typesafe projected $42.26 > budget $20.00

### base no reuse (660,609 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 686,477,590 | 131,141,126 | $57.66 |
| verify | claude-haiku-5-5 | 107,310 | 28,718 | $0.05 |
| group | claude-haiku-5-5 | 6,583 | 865 | $0.00 |
| memo | claude-sonnet-5-5 | 6,382 | 2,182 | $0.07 |

- Known API cost by provider: {'typesafe': 57.66, 'anthropic': 0.12}
- Unknown-cost providers: none
- Enrichment time (modeled, 8 workers): **3.84 h**
- ⚠ OVER BUDGET: typesafe projected $57.66 > budget $20.00

### conservative reuse (484,189 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 523,075,913 | 99,925,715 | $43.94 |
| verify | claude-haiku-5-5 | 127,750 | 34,188 | $0.06 |
| group | claude-haiku-5-5 | 7,837 | 1,030 | $0.00 |
| memo | claude-sonnet-5-5 | 7,598 | 2,598 | $0.08 |

- Known API cost by provider: {'typesafe': 43.94, 'anthropic': 0.14}
- Unknown-cost providers: none
- Enrichment time (modeled, 8 workers): **2.92 h**
- ⚠ OVER BUDGET: typesafe projected $43.94 > budget $20.00

### conservative no reuse (660,609 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 713,664,821 | 136,334,834 | $59.95 |
| verify | claude-haiku-5-5 | 127,750 | 34,188 | $0.06 |
| group | claude-haiku-5-5 | 7,837 | 1,030 | $0.00 |
| memo | claude-sonnet-5-5 | 7,598 | 2,598 | $0.08 |

- Known API cost by provider: {'typesafe': 59.95, 'anthropic': 0.14}
- Unknown-cost providers: none
- Enrichment time (modeled, 8 workers): **3.99 h**
- ⚠ OVER BUDGET: typesafe projected $59.95 > budget $20.00

## Refreshed estimates from later checkpoints

| checkpoint | texts | workers | texts/s | failed calls | in/text | out/text | full-run Jev tokens (in / out) | hours at same workers | Jev cost |
|---|---|---|---|---|---|---|---|---|---|
| checkpoint_500 | 279 | 2 | 15.81 | 0 | 1029.1 | 196.5 | 498,258,248 / 95,147,477 | 8.51 | $41.85 |
| analysis_10000 | 8,448 | 4 | 32.51 | 0 | 1077.1 | 196.5 | 521,535,344 / 95,156,378 | 4.14 | $43.81 |

## Controls

- Budgets: {'anthropic': 18.0, 'typesafe': 20.0} · output-token caps per call: {'enrich': 300, 'verify_per_review': 60, 'group': 600, 'memo': 6000}
- Max workers 8 · declared max fallback fraction 0.0
- Jev derived blended rate from balance reconciliation: not yet reconciled
- Local compute: unknown (laptop; not metered) - reported separately from API spend, never as zero.
