# One review, end to end

All values below are read from the saved full run (`work/full.sqlite`, exported in `grading/`).

## The review

| Field | Value |
|---|---|
| `review_id` | `962280d7-15ec-4842-87b9-235a0f55fee1` (source row 527,670) |
| `review_text` | "Unable to fast-forward song & replay it..Auto shuffle cannot be turned off. Disappointed since last update!" |
| `review_rating` | 1 (kept as metadata - not sent to any model) |
| `review_timestamp` | 2023-09-23 19:33:17 · `app_version` missing |
| `source_sha256` | `ac51749b562ebeb64730239880a4b43680d38a1457d50745bb02536b7587a4ea` (contract `row_sha`) |

## 1 · Ingest (code)

Read with the course's own CSV parser; row hash computed with the provided `row_sha`. Its exact text is
unique in the corpus, so it is its own canonical ID and no other record reuses its result.

## 2 · Enrich (Jev)

One request, review text only, four questions (`labels-v3`):

| Call | Value |
|---|---|
| `request_id` | `local-4c4a7e54-c7f0-4f1c-83b0-77a2a37fe365` |
| model / phase / outcome | `jev-1.13.0` / `initial` / `succeeded` (attempt 1, 0.093 s) |
| usage | 1,080 input + 198 output tokens |

Validated record (`grading/records.jsonl.gz`):

```json
{"review_id":"962280d7-15ec-4842-87b9-235a0f55fee1","status":"completed","topic":"usability","intent":"complaint",
 "severity":3,"sentiment":-0.57,"entities":["shuffle","song","update"],
 "evidence_quote":"Unable to fast-forward song & replay it..Auto shuffle cannot be turned off. Disappointed since last update!",
 "needs_review":false,"label_config":"jev-1.13.0+labels-v3+schema-v1"}
```

Severity 3 because controls are restricted (no fast-forward, forced shuffle) but music still plays; the
quote is the whole text because the review is under 200 characters.

## 3 · Verify (Claude Haiku 5.5)

Selected by the hash-seeded random sample (968 of 484,189 distinct texts). The verifier saw only the text and
definitions in request `req_011Cg6qskhA7UVYsm5y1sqq9` and returned **usability / complaint / 3** -
agreement on all three fields.

## 4 · Group (code + Claude Haiku 5.5)

Code assigned it to **ISS-USABILITY** because it is a completed complaint with topic `usability`
(`grading/membership.csv`: `ISS-USABILITY,962280d7-…`). Haiku named the issue from a random 15-quote pack:
"Excessive unskippable ads and playback interruptions".

## 5 · Rank (code)

ISS-USABILITY: 81,495 members, severity sum 232,048 (this review contributes 3), mean 2.847389,
priority score 232,048 → **rank 1** (`grading/ranking.csv`).

## 6 · Memo claim

`outputs/full/memo.md`: "ISS-USABILITY has 81495 complaints [ISS-USABILITY.complaint_count] and a severity sum
of 232048 [ISS-USABILITY.severity_sum]" - both claim IDs exist in `grading/claims.csv` with those values, and
`memo_checks.json` confirms every cited ID was supplied and its value appears in the prose. The memo's own
quoted example for the same issue (`ae776e66-…`, "no option to turn off shuffle") describes the same
forced-shuffle problem as this review.

---

## A failed case and how it was handled

`88c23440-1620-47ac-9b8e-ca7fbd545bae`, during the resume phase:

| Attempt | Time (UTC) | Outcome |
|---|---|---|
| 1 | 2026-10-16 19:33:11 | `failed` - `TypeSafeAPIConnectionError` (host lost network; DNS lookups failing) |
| 2 | 2026-10-16 22:11:34 | `succeeded` → other / complaint / 2 |

Decision recorded by code: connection errors are transient, so the review was retried with backoff rather than
quarantined; the circuit breaker did not trip because successes resumed before 25 consecutive reviews failed.
Both attempts are in `grading/calls.jsonl.gz`. The failed attempt has no provider usage (no response was
received); it is exported with `input_tokens: 0, output_tokens: 0` and
`usage_source: "none_returned: …"` rather than an invented figure.

## An ambiguous case

`0a32611b-79ca-4e0d-8536-f4c76b48e670` - "Lags a lot! Irritating app!!😑 Totally disappointed 🙁"

Jev: playback (0.99) / complaint (1.00) / **severity 3 with confidence 0.47** (probabilities 2: 0.41, 3: 0.58).
Code set `needs_review: true` because severity confidence fell below 0.5. Under the shared scale, "lags a lot"
is a degraded function (3) unless the lag stops playback entirely (4); the text doesn't say, so the label is
kept and flagged rather than invented. 100,316 completed records (15.2%) carry this flag.
