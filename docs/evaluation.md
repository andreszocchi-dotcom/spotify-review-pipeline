# Evaluation

Three independent checks, each saved with its raw cases:

1. **Golden 50** — human labels vs the pipeline's full-run predictions ([`evals/golden_eval.json`](../evals/golden_eval.json)).
2. **Independent verifier** — Claude Haiku 5.5 re-labels a declared random sample without seeing Jev's answer
   ([`outputs/full/verify_report.json`](../outputs/full/verify_report.json)).
3. **System tests** — malformed output, API failures, spend cap, circuit breaker, model drift, empty text,
   prompt injection, planted wrong label ([`evals/system_tests.json`](../evals/system_tests.json)).

## 1. Golden 50 (human labels)

Procedure: the 50 reviews in `data/golden_50_to_label.csv` were labelled by hand in
`labels/golden_50_labeling.xlsx` using only the contract definitions, then exported with validation
(`python -m pipeline.golden export`). They were never used in prompts, examples, thresholds or tuning;
label tuning used development checkpoints only ([prompt_iterations.md](../evals/prompt_iterations.md)).
Their texts went through the normal full-corpus run, so predictions are the real production labels.

Predeclared scoring: exact agreement for topic and intent (plus macro F1); severity exact, within-1 and MAE;
sentiment agrees when |pred − human| ≤ 0.25, plus MAE; `evidence_quote` must be an exact source substring;
`needs_review` is scored as a prediction of the human "ambiguous" flag. Missing or quarantined predictions
count as wrong.

<!-- GOLDEN:START -->
_Pending: human labels not yet exported. Run `python -m evals.golden_eval --db work/full.sqlite` once
`evals/golden_50_human.csv` exists._
<!-- GOLDEN:END -->

## 2. Independent verification

The verifier is a different model family (Claude Haiku 5.5, effort low) given the review text and the same
written definitions, but never the first prediction. The sample is chosen by SHA-256 of a fixed seed + text
hash, so it is random with respect to content and reproducible. Code compares the labels.

| Run | Sample | Topic | Intent | Severity exact | Severity MAE | Disagreements |
|---|---|---|---|---|---|---|
| checkpoint 500 (labels-v1) | 96 | 87.5% | 95.8% | 81.3% | 0.198 | 30 |
| analysis 10,000 (labels-v3) | 253 | 79.8% | 88.5% | 81.0% | 0.206 | 102 |
| **full corpus (labels-v3)** | **968** | **85.0%** | **90.5%** | **77.7%** | **0.249** | **370** |

Full-run note: 3 of 39 verifier batches first hit the output cap (thinking tokens count toward it); the cap was raised and only those 68 reviews were re-sent (6 failed attempts logged).

Disagreement patterns (case lists in each `verify_report.json`): Jev rates emphatic generic complaints at
severity 3–4 where the verifier says 2; premium-locked controls split between `usability` and `billing`;
and `other` vs a specific topic for vague complaints. Agreement between two models is not accuracy: where
both are wrong in the same way, this check cannot see it — that is what the golden set is for.

## 3. System tests

`python -m evals.system_tests` (offline, stub client) and `--paid` (real Jev + Claude calls on synthetic
reviews kept in a separate test database, never in business results).

| Test | Outcome |
|---|---|
| Malformed output (invalid topic) → one retry → accepted | PASS |
| Invalid output twice → quarantined with reason, no third paid attempt | PASS |
| Temporary 429 → backoff, both failed attempts logged, then success | PASS |
| Persistent failure → stops at the retry bound, quarantined | PASS |
| Spend cap → no call admitted once spent + reservation would exceed the cap | PASS |
| Account-level error (revoked key / no credit) → run stops, review left pending | PASS |
| Circuit breaker → 25 consecutive failed reviews stop the run | PASS |
| Model drift (served model ≠ pinned `jev-1.13.0`) → rejected | PASS |
| Empty review text → quarantined at ingest (`empty_review_text`) | PASS |
| Prompt injection ×3 ("ignore previous instructions…", fake SYSTEM line, fake `</review>` tag) → enrichment labels unchanged | PASS ×3 |
| Prompt injection → verifier labels unchanged | PASS ×2 |
| Deliberately wrong label planted in a test copy → caught by the verifier | PASS |

## 4. Recovery in production

The full run was interrupted on purpose after 400 batches (20,000 distinct texts →
[`grading/checkpoint_before.json`](../grading/checkpoint_before.json): 28,908 completed review IDs including
exact-duplicate reuse), then resumed with the same command (`phase = resume`). The resume issued no
enrichment call for any text already completed under the same `label_config`
([`grading/checkpoint_after.json`](../grading/checkpoint_after.json)).

The run also survived an unplanned stall: the host lost network/slept for ~2.5 h during the resume phase.
11 calls failed with `TypeSafeAPIConnectionError` (DNS), were retried with backoff, and the run continued
without quarantining anything once connectivity returned (visible in `grading/calls.jsonl.gz` as
`outcome: "failed"` attempts followed by successes).
