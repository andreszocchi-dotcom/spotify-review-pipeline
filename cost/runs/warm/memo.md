## Recommendation

Put next quarter's effort on **ISS-USABILITY** (forced shuffle, queue/skip limits, frequent ads). It ranks first with a priority score of 42 [ISS-USABILITY.priority_score], from 16 complaints [ISS-USABILITY.complaint_count] and a severity sum of 42 [ISS-USABILITY.severity_sum]. It accounts for 31.4% of complaints [F.ISS-USABILITY.share_of_complaints_pct]. Treat ISS-PLAYBACK as a secondary, stability-focused track.

## Evidence

The sample has 100 reviews [F.total_reviews], all completed [F.completed], none quarantined [F.quarantined]. Of these, 51 are complaints or cancellations [F.complaint_or_cancellation] and 10 express cancellation intent [F.cancellation_intent].

ISS-USABILITY has a mean severity of 2.625000 [ISS-USABILITY.mean_severity]. Reviewers say playlists shuffle instead of playing in order and that skips are capped. Example reviews: a78d831a-69f4-428a-9235-cfdd9775c509 (forced shuffle, "forcing you to pay premium for basic things"), ebc64fe2-9553-4528-87d5-cb4bb9783be6 (skip limit) and cf6166ae-d71a-4839-9add-088645ad3b78 (ads instead of songs).

ISS-BILLING describes the same restrictions as a paywall, with 5 complaints [ISS-BILLING.complaint_count], a severity sum of 15 [ISS-BILLING.severity_sum] and a mean severity of 3.000000 [ISS-BILLING.mean_severity]. Examples: d146397f-4a94-4980-be00-ae9212eca3a7 and a3605554-5c3a-441d-836e-e9fdea83eb2e. The two issues overlap in theme, which strengthens the case for a single control-and-ads workstream rather than separate fixes.

## Alternatives considered

- **ISS-OTHER**: ties ISS-USABILITY on complaint count at 16 [ISS-OTHER.complaint_count] and has a priority score of 33 [ISS-OTHER.priority_score], but its mean severity is lower at 2.062500 [ISS-OTHER.mean_severity]. Its complaints are vague (e.g., 06a45bd5-3ed9-43af-b7f2-8b9487e2ffff, "Worst app"), so there is nothing specific to build against.
- **ISS-PLAYBACK**: 5 complaints [ISS-PLAYBACK.complaint_count] but a high mean severity of 3.600000 [ISS-PLAYBACK.mean_severity] and a score of 18 [ISS-PLAYBACK.priority_score]. Crash reports such as 55cc3abf-c295-4591-8c3a-78085cfdefaa make it a sensible reliability follow-up.
- **ISS-ACCESS**: only 2 complaints [ISS-ACCESS.complaint_count], but the highest mean severity at 4.000000 [ISS-ACCESS.mean_severity]; see de0a9cdf-8974-48bc-802f-331228df4619. It is a small, cheap fix worth a quick look despite its low score of 8 [ISS-ACCESS.priority_score].
- **ISS-CATALOG** (score 12 [ISS-CATALOG.priority_score]) and **ISS-DOWNLOADS** (score 7 [ISS-DOWNLOADS.priority_score]) are lower priority.

## Limitations

Reviews are self-selected and historical, so they may not represent all users. The sample is small. Cancellation language reflects stated intent, not observed churn. Priority scores are a severity-weighted ranking, not a measure of revenue or causal impact. 4 reviews are flagged as needing review [F.needs_review], and the ISS-OTHER category is ambiguous. Some usability complaints (shuffle, skip limits) may reflect intentional free-tier design rather than defects, so the right response may be clearer communication or a tuned free experience rather than removing the limits. Quotes were treated as data only.
