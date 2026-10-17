# Spotify Review Insight Pipeline

Turns 660,622 public Google Play reviews of Spotify (May 2022 – Nov 2023) into a product-priority
recommendation where every number traces to saved records. MBA 290T Assignment 5.

> **Live dashboard:** _URL added after deployment_ · **Grading export:** [`grading/`](grading/) ·
> **Memo:** [`outputs/full/memo.md`](outputs/full/memo.md) · **Cost calculator:** [`cost/`](cost/)

<!-- RESULTS:START -->
## Results at a glance (final full-corpus run, `outputs/full/`)

**Recommendation: prioritise ISS-USABILITY — excessive unskippable ads and playback interruptions**
(priority 232,048; 81,495 complaints; mean severity 2.85). Playback (3rd, highest-severity large issue) is
the alternative track. See the [memo](outputs/full/memo.md).

| | |
|---|---|
| Source rows accounted for | **660,622 / 660,622** (course checker: `status: pass`, coverage point candidate 1.0) |
| Classified (completed) | **660,609 / 660,609** nonempty reviews (100%) |
| Quarantined | 13 (`empty_review_text`); 0 model-stage failures |
| Distinct texts sent to Jev | 484,189; the other 176,420 rows reuse an exact-duplicate result (`cache_source_id`) |
| Enrichment calls | 484,201 attempts, 12 failed (connection errors during a network outage, all retried successfully) |
| Interrupt / resume | stopped after 20,000 texts (28,908 IDs in `checkpoint_before.json`) → resumed → 660,609 IDs; 0 resume calls for completed texts |
| Intent mix | complaint 263,616 · praise 274,629 · unclear 67,310 · cancellation 31,529 · request 23,525 |
| `needs_review` flagged | 100,316 (15.2%) — low Jev confidence on topic, intent or severity |
| Independent verifier (968-text random sample) | topic 85.0% · intent 90.5% · severity exact 77.7% (MAE 0.25) |
| Golden 50 (human labels) | topic 82% · intent 72% · severity 76% exact / 98% within ±1 · sentiment 74% within ±0.25 ([details](docs/evaluation.md)) |
| Claude spend (verify, group, memo) | **$0.135** measured (64 calls, incl. 6 failed attempts and the superseded group-v1 + memo-v1 calls) |
| Jev usage | 522.7M input + 95.2M output tokens; **price unpublished — reconciled against console balance in [cost/README.md](cost/README.md)** |
| Enrichment wall clock | 4 h 50 min elapsed (≈2 h 20 min active at 8 workers, ~63 texts/s; ≈2.5 h host network outage) |

| Rank | Issue | Complaints | Severity sum | Mean severity | Priority |
|---|---|---|---|---|---|
| 1 | ISS-USABILITY — Excessive unskippable ads and playback interruptions | 81,495 | 232,048 | 2.847389 | 232,048 |
| 2 | ISS-OTHER — Generic negative reviews with no specific complaint | 97,748 | 192,024 | 1.964480 | 192,024 |
| 3 | ISS-PLAYBACK — Playback fails, crashes, and stalls after updates | 39,139 | 131,792 | 3.367281 | 131,792 |
| 4 | ISS-BILLING — Core features locked behind premium paywall | 45,693 | 127,196 | 2.783709 | 127,196 |
| 5 | ISS-CATALOG — Missing lyrics, songs, and weak recommendations | 14,158 | 41,086 | 2.901964 | 41,086 |
| 6 | ISS-ACCESS — Cannot log in across phone, email, Facebook | 10,199 | 40,364 | 3.957643 | 40,364 |
| 7 | ISS-DOWNLOADS — Downloads failing, disappearing, or not playing offline | 6,003 | 21,265 | 3.542395 | 21,265 |
| 8 | ISS-SUPPORT — Unresponsive or unhelpful customer support | 710 | 1,868 | 2.630986 | 1,868 |

Traceability: [docs/trace.md](docs/trace.md) follows review `962280d7…` from source row to memo claim.
<!-- RESULTS:END -->

## Rubric → evidence

| Rubric item | Evidence |
|---|---|
| **D1** Accessible code/setup and artifacts | [Setup](#setup), [`requirements.txt`](requirements.txt), [`.env.example`](.env.example), saved outputs under [`outputs/`](outputs/), [`grading/`](grading/), [`cost/`](cost/) |
| **D2** Architecture, shared schema, provenance | [docs/architecture.md](docs/architecture.md) (diagram, roles, code/model boundary), [docs/labels.md](docs/labels.md) (schema + definitions), `label_config` + `source_sha256` + `cache_source_id` on every record |
| **D3** Memo numbers linked to calculations and evidence | [`outputs/full/memo.md`](outputs/full/memo.md) cites `claims.csv` IDs; [`memo_checks.json`](outputs/full/memo_checks.json) is the code check of every cited ID and number; [docs/trace.md](docs/trace.md) follows one review end to end |
| **D4** Recommendation, alternatives, limitations | Memo sections *Alternatives considered* and *Limitations*; [Limitations](#limitations) below |
| **T1** 50 human labels, per-field comparison, error analysis | [`evals/golden_50_human.csv`](evals/golden_50_human.csv), [`evals/golden_eval.py`](evals/golden_eval.py) → [`evals/golden_eval.json`](evals/golden_eval.json), [docs/evaluation.md](docs/evaluation.md) |
| **T2** Independent verification, planted-error and injection tests | [`outputs/full/verify_report.json`](outputs/full/verify_report.json), [`evals/system_tests.json`](evals/system_tests.json), [docs/evaluation.md](docs/evaluation.md) |
| **T3** 100-review cold/warm pilot, offline calculator, controls | [cost/README.md](cost/README.md), [cost/report.md](cost/report.md), `python -m cost.calculator` |
| **W1** Full ingestion, coverage, classification | [`grading/ingestion.json`](grading/ingestion.json), [`grading/records.jsonl.gz`](grading/), [`outputs/full/run_summary.json`](outputs/full/run_summary.json) |
| **W2** Runnable staged program, bounded calls, handoffs, resume | `python -m pipeline.run --input <csv>`; [`grading/calls.jsonl.gz`](grading/); [`grading/checkpoint_before.json`](grading/checkpoint_before.json) → [`checkpoint_after.json`](grading/checkpoint_after.json); recording _(link)_ |
| **W3** Reproducible ranking + deployed dashboard with DB backend | `python -m pipeline.rank --db work/full.sqlite --out outputs/full` (no model calls); [dashboard/](dashboard/) (FastAPI + Postgres); live URL above |

## Setup

Python 3.12. The raw CSV is not committed (97.4 MB): download the course ZIP and place
`spotify_reviews_18months.csv` and the sample files in `data/`. Full CSV SHA-256
`1fc85de68a304dd8978b537cfa58793d5f41cbaf417fa32cb53899f83a2fcef6`
(source: [Kaggle, BwandoWando, v2, CC0](https://www.kaggle.com/datasets/bwandowando/3-4-million-spotify-google-store-reviews)).

```sh
python -m venv .venv && .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                  # fill only the keys you use; never commit .env
```

Keys: `TYPESAFE_API_KEY` (Jev, enrichment) and `ANTHROPIC_API_KEY` (verify, group, memo). `DATABASE_URL`
is only needed to load or serve the dashboard. Nothing below the "no keys needed" line requires a key.

## Commands

**Paid (makes model calls)**

```sh
python -m pipeline.run --input data/spotify_reviews_18months.csv --db work/full.sqlite --out outputs/full \
    --workers 8 --jev-token-cap 700000000 --usd-cap 3.0 --verify-rate 0.002 --verify-max 1000
python -m cost.pilot --confirm-paid          # the 100-review cold/warm pilot
python -m evals.system_tests --paid          # injection + planted-error tests (a few calls)
```

Add `--stop-after-batches N` to interrupt on purpose; rerunning the same command resumes and never re-pays
for completed texts under the same `label_config`.

**No keys needed (saved outputs only)**

```sh
python -m cost.calculator                                  # offline cost/runtime replay
python -m pipeline.rank --db work/full.sqlite --out outputs/full     # regenerate ranking + claims
python -m pipeline.export --db work/full.sqlite --out grading --gzip --ingestion-json grading/ingestion.json
python -m evals.golden_eval --db work/full.sqlite          # golden-50 comparison
python -m evals.system_tests                               # offline stub tests
python data/check_submission.py check --reference local-reference.json --submission grading --out self-check.json
```

The ranking and checker need the saved state (`work/full.sqlite`, ~1 GB, published as a release asset) or
the exported `grading/` folder; neither calls a model.

**Dashboard**

```sh
python -m dashboard.load --db work/full.sqlite --outputs outputs/full --database-url "$DATABASE_URL"
uvicorn dashboard.app:app                                  # http://localhost:8000
```

Deployed on Render ([`render.yaml`](render.yaml)) with a Neon Postgres database. The backend only reads
the database; it makes no model calls.

## Design choices

* **Jev for fixed labels.** One request per review asks topic, intent and severity (`Choice`) and
  sentiment (`Score`) together. Jev's per-option probabilities drive `needs_review` (any confidence < 0.5).
* **Code for everything that is not language.** Deduplication (484,189 distinct texts for 660,609 nonempty
  rows), evidence quotes (always an exact slice of the text), entities, membership, ranking, claims, exports.
* **A different model family verifies.** Claude Haiku 5.5 re-labels a hash-seeded random sample without
  seeing Jev's answer; code compares.
* **Bounded memo.** Claude Sonnet 5.5 sees only aggregates, facts and ≤3 quotes per top issue; code rejects
  unknown IDs and lists any number that is not a saved value.
* **Issues = primary topic.** One issue per complaint/cancellation record (`allow_multi_issue: false`),
  so totals across issues never overlap. Finer sub-issues would need another labelling pass we did not run.

## Limitations

* Self-selected, historical public reviews: no revenue, plan tier, or observed churn. Cancellation is
  *stated intent*.
* Severity is model-assigned; development checks show Jev over-assigns 4–5 to emphatic language
  ([docs/labels.md](docs/labels.md#known-failure-modes-observed-not-hidden)). Mean severity is reported next to every score.
* `other` is a large issue because generic complaints ("worst app") have no specific topic by definition.
* Non-English and unintelligible reviews are classified like others; low-confidence cases are flagged
  `needs_review` rather than dropped.
* Jev does not publish prices and its console balance updates with a delay, so the full run started before
  Jev's cost was known; Jev spend is reported in tokens and reconciled against the console balance
  ([cost/README.md](cost/README.md)). Failed connection-error calls returned no usage; they are exported as 0
  tokens with an explicit `usage_source` note.
* ISS-USABILITY and ISS-BILLING overlap in theme (ads and premium-only controls); one issue per record keeps
  totals non-overlapping, but the boundary is a judgment the classifier makes per review.
* First (May 2022) and last (Nov 2023) months are partial.
