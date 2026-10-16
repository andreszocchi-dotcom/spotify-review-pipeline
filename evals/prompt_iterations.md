# Label prompt iterations (development data only)

All tuning used `checkpoint_500.csv` development reviews. The golden 50 were never used for tuning,
prompts, examples or thresholds.

| Version | Change | Topic / intent / severity agreement with the independent Haiku verifier |
|---|---|---|
| labels-v1 | Contract definitions as written | 96-review random sample: topic 87.5%, intent 95.8%, severity exact 81.3% (MAE 0.198); 30 disagreements |
| labels-v2 | Premium-locked controls moved to `billing`; generic verdicts ("useless", "worst app") pinned to severity 2; severity 3/4 examples | On the 30 v1-disagreement cases: topic 15, intent 26, severity 16 (v1: 18, 26, 12) |
| labels-v3 | v1 topic definitions + v2 severity wording | On the same 30 cases: topic 18, intent 26, severity 16 → **chosen** |

Observed v1 failure patterns (dev500 disagreement report, `outputs/dev500/verify_report.json`):

1. Generic negative verdicts with no described functional loss rated severity 3-4 instead of 2.
2. Premium-only controls (skip limits, can't pick songs) labelled `usability`; the verifier and contract
   lean to `billing`. Broadening the `billing` definition (v2) over-shifted other topics, so v3 reverts it.
3. Occasional intent noise ("Best app for listening music" → `request`).

Caveats: the 30 cases were selected *because* v1 disagreed, so some gain is regression to the mean; the
verifier is another model, not ground truth. The golden-50 comparison is the real accuracy check.
Experiment cost: 60 Jev calls run ad hoc, outside the pipeline call log. The v2 run measured 33,113 input /
5,913 output tokens; the v3 run's usage was not recorded (same 30 texts, similar prompt length, so roughly the same).
