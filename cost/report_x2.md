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
| jev-1.13.0:input_tokens | unknown USD per 1,000,000 tokens | 2026-10-16 | https://docs.typesafe.ai/primitives/choice |
| jev-1.13.0:output_tokens | unknown USD per 1,000,000 tokens | 2026-10-16 | https://docs.typesafe.ai/primitives/choice |

## Measured cold run

- End-to-end wall clock **44.511 s** · throughput 2.25 rows/s
- Stage seconds: {'ingest': 0.205, 'enrich': 13.251, 'verify': 6.414, 'group': 10.406, 'rank': 0.006, 'memo': 13.996}
- Result-cache hits: 0 · enrichment calls: 100
- Known API spend **$0.0686** + unknown-rate items ['jev-1.13.0:input_tokens', 'jev-1.13.0:output_tokens']
- Known cost per 1,000 rows $0.6865 · per completed record $0.000686

| stage | provider | model | attempts | failed | input | cache read | cache write | output | cost |
|---|---|---|---|---|---|---|---|---|---|
| enrich | typesafe | jev-1.13.0 | 100 | 0 | 102,887 | 0 | 0 | 19,655 | unknown |
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
| enrich | jev-1.13.0 | 503,149,212 | 96,119,021 | unknown |
| verify | claude-haiku-5-5 | 107,310 | 28,718 | $0.05 |
| group | claude-haiku-5-5 | 6,583 | 865 | $0.00 |
| memo | claude-sonnet-5-5 | 6,382 | 2,182 | $0.07 |

- Known API cost by provider: {'anthropic': 0.12}
- Unknown-cost providers: ['typesafe']
- Enrichment time (modeled, 8 workers): **2.81 h**
- ⚠ typesafe: cost unknown (no published rate) - cannot confirm it fits the $20.00 budget

### base no reuse (660,609 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 686,477,590 | 131,141,126 | unknown |
| verify | claude-haiku-5-5 | 107,310 | 28,718 | $0.05 |
| group | claude-haiku-5-5 | 6,583 | 865 | $0.00 |
| memo | claude-sonnet-5-5 | 6,382 | 2,182 | $0.07 |

- Known API cost by provider: {'anthropic': 0.12}
- Unknown-cost providers: ['typesafe']
- Enrichment time (modeled, 8 workers): **3.84 h**
- ⚠ typesafe: cost unknown (no published rate) - cannot confirm it fits the $20.00 budget

### conservative reuse (484,189 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 523,075,913 | 99,925,715 | unknown |
| verify | claude-haiku-5-5 | 127,750 | 34,188 | $0.06 |
| group | claude-haiku-5-5 | 7,837 | 1,030 | $0.00 |
| memo | claude-sonnet-5-5 | 7,598 | 2,598 | $0.08 |

- Known API cost by provider: {'anthropic': 0.14}
- Unknown-cost providers: ['typesafe']
- Enrichment time (modeled, 8 workers): **2.92 h**
- ⚠ typesafe: cost unknown (no published rate) - cannot confirm it fits the $20.00 budget

### conservative no reuse (660,609 texts classified)

| stage | model | input | output | cost |
|---|---|---|---|---|
| enrich | jev-1.13.0 | 713,664,821 | 136,334,834 | unknown |
| verify | claude-haiku-5-5 | 127,750 | 34,188 | $0.06 |
| group | claude-haiku-5-5 | 7,837 | 1,030 | $0.00 |
| memo | claude-sonnet-5-5 | 7,598 | 2,598 | $0.08 |

- Known API cost by provider: {'anthropic': 0.14}
- Unknown-cost providers: ['typesafe']
- Enrichment time (modeled, 8 workers): **3.99 h**
- ⚠ typesafe: cost unknown (no published rate) - cannot confirm it fits the $20.00 budget

## Controls

- Budgets: {'anthropic': 18.0, 'typesafe': 20.0} · output-token caps per call: {'enrich': 300, 'verify_per_review': 60, 'group': 600, 'memo': 6000}
- Max workers 8 · declared max fallback fraction 0.0
- Jev derived blended rate from balance reconciliation: not yet reconciled
- Local compute: unknown (laptop; not metered) - reported separately from API spend, never as zero.
