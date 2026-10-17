# Labels: shared definitions, how they were applied, and known failure modes

The primary labels are exactly those in `data/GRADING_CONTRACT.md`. The classifier's wording lives in
[`pipeline/labels.py`](../pipeline/labels.py) (prompt version `labels-v3`; label config
`jev-1.13.0+labels-v3+schema-v1`). Every completed record carries that `label_config`.

## Output schema (one record per source review)

| Field | Type | Produced by |
|---|---|---|
| `topic` | one of 8 topics | Jev `Choice` |
| `intent` | `cancellation` > `complaint` > `request` > `praise` > `unclear` (precedence) | Jev `Choice` |
| `severity` | integer 1–5 | Jev `Choice` over five defined levels |
| `sentiment` | −1…1 | Jev `Score` over five levels, mapped `score / 2 − 1` |
| `evidence_quote` | exact substring of the review | code: whole text if ≤200 chars, else the sentence with most topic terms |
| `entities` | feature terms literally present | code: keyword match (≤8 terms) |
| `needs_review` | bool | code: any of topic/intent/severity confidence < 0.5 |
| `status`, `reason`, `cache_source_id` | provenance | code |

Stars, likes and app version are kept as metadata and are **never** sent to the classifier
(`classification_input_fields = ["review_text"]`).

## Topic decisions

| Topic | Contract definition | Applied example (dev data, ID prefix) | Label |
|---|---|---|---|
| access | Login, signup, password or account access | `305c3fe1` "Unable to login, can not reach tech support. Looks like the account was hacked." | access / complaint / 5 (privacy harm stated) |
| usability | Navigation, controls, layout, queue/playlist, ad interruptions | `a0f91c48` "I uninstalled this app after update. I am unable to shuffle any song." | usability / cancellation / 4 |
| playback | Playback failure, crashes, lag, connection, audio | `8503f550` "Why can't I use the app for a few days now? I tried uninstalling installing…" | playback / complaint / 4 |
| downloads | Downloading, saved music, offline, disappearing downloads | `a405a67b` "…app crashes and both parties lost entire downloaded music. No support or fix" | downloads / complaint / 5 (data loss) |
| catalog | Missing songs, search/discovery, recommendations, lyrics | `eeecb368` "My lyrics aren't showing still after a month!" | catalog / complaint (severity: see failures) |
| billing | Price, charges, subscriptions, paywalls, premium entitlement | `41c0c736` "I had unsubscribed, and Spotify stole My money!!!" | billing / cancellation / 5 (financial harm) |
| support | Contacting support and the response | `31b4c031` "…after texting spotify they fixed that bug. thankyou" | support / praise |
| other | General praise/criticism, unrelated, no specific topic | "Great" / "Good at all" (pilot) | other / praise / 1 |

Rules applied: highest supported severity wins, then first mentioned; a paid-plan mention alone is not
`billing`; general praise is `other`; bare boycott slogans are `unclear`
(`1452ccc8` "Boycott Sweden" → other / unclear).

## Severity scale with examples

| Level | Meaning | Example |
|---|---|---|
| 1 | No reported problem (praise, unclear, pure request) | "Great" |
| 2 | Generic criticism / annoyance, no functional loss | "the update ruined it" with no described loss (rule added in labels-v2/v3) |
| 3 | Degraded or restricted function, some use remains | skip limits, frequent ads, intermittent errors |
| 4 | Core task clearly blocked | "Why can't I use the app for a few days now?" |
| 5 | Explicit serious financial, privacy or data harm | "stole My money", "account was hacked", "lost entire downloaded music" |

## Known failure modes (observed, not hidden)

These are real development-set predictions that look wrong under the shared definitions. They are
reported in the evaluation rather than patched by hand:

| ID prefix | Text (shortened) | Predicted | Why it looks wrong |
|---|---|---|---|
| `6597a459` | "I DIDNT MEAN TO PUT ON PREMIUM HOW DO I TAKE IT OFF" | billing / cancellation / 5 | No stated financial harm; closer to billing / request or complaint, severity 3 |
| `eeecb368` | "My lyrics aren't showing still after a month!" | catalog / complaint / 4 | Lyrics missing is degraded, not a blocked core task → 3 |
| `1cb86bb1` | "couldn't listen even one song without adds" | usability / complaint / 4 | Ads interrupt but playback works → 3 |
| `8a38dea1` | Unintelligible text | access / unclear / 4 | Unclear content should be severity 1 (flagged `needs_review`) |
| `68a5d92a` | "very bad app … data has hacking for our mobile" | other / complaint / 5 | Vague claim; severity 5 needs explicit harm |

Pattern: Jev over-assigns severity 4–5 when language is emphatic. Many of these carry `needs_review = true`.
The independent verifier (Claude Haiku) measures the size of this effect on random samples
(see [evaluation.md](evaluation.md)); ranking results are therefore reported with mean severity, and the
memo is told that severity is model-assigned.
