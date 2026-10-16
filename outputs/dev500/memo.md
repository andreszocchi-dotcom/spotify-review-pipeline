## Recommendation

Prioritize **ISS-USABILITY** (post-update navigation, shuffle, and skip regressions) for next quarter. It ranks first with a priority score of 170 [ISS-USABILITY.priority_score], ahead of ISS-OTHER at 145 [ISS-OTHER.priority_score]. Treat ISS-PLAYBACK as a close-second reliability track, because its complaints are the most severe of the large issues.

## Evidence

- ISS-USABILITY has 65 complaints [ISS-USABILITY.complaint_count], a severity sum of 170 [ISS-USABILITY.severity_sum], and a mean severity of 2.615385 [ISS-USABILITY.mean_severity]. It accounts for 27.0 percent of complaints [F.ISS-USABILITY.share_of_complaints_pct].
- The corpus holds 500 reviews [F.total_reviews], of which 241 are complaint or cancellation [F.complaint_or_cancellation].
- Example reviews describe a cluttered layout and hard-to-find mixes (2aae0ce4-ae4a-46ce-b2fe-0d901eb23c06), a changed shuffle with lost rewind and forward (c13dcedc-50da-48a8-a90d-cfb037a66478), and a skip limit (6ba8fc67-700c-4d33-ad84-ef67a05b2ae1).
- ISS-PLAYBACK has 35 complaints [ISS-PLAYBACK.complaint_count] but a mean severity of 3.485714 [ISS-PLAYBACK.mean_severity]. Examples include a black screen requiring reinstall (065c418e-7f18-42a3-b241-fe693b7a2b0c) and a user who abandoned a new Premium signup (a7b7539a-c8d3-4f4e-9edd-d46cd1b1fd12).
- Cancellation intent appears in 29 reviews [F.cancellation_intent]. This is stated intent only, not observed churn.

## Alternatives considered

- **ISS-OTHER**: Highest complaint count at 74 [ISS-OTHER.complaint_count] and 30.7 percent of complaints [F.ISS-OTHER.share_of_complaints_pct]. Its mean severity is the lowest of the top four at 1.959459 [ISS-OTHER.mean_severity]. Its reviews are generic, such as 3feb5ba7-4a0d-47e0-a803-eb2dce85dd5e, so they are not actionable without further classification.
- **ISS-PLAYBACK**: Score of 122 [ISS-PLAYBACK.priority_score]. Strong candidate if severity is weighted over volume.
- **ISS-BILLING**: 36 complaints [ISS-BILLING.complaint_count] and score of 106 [ISS-BILLING.priority_score]. Much of it concerns features locked behind Premium (d146397f-4a94-4980-be00-ae9212eca3a7), which overlaps with the skip complaints in ISS-USABILITY and may be a business decision rather than a defect. One review reports paying yet being blocked (16929558-ce1e-4b87-8738-a1de3f557f66).
- **ISS-ACCESS**: Only 10 complaints [ISS-ACCESS.complaint_count] but mean severity of 4.000000 [ISS-ACCESS.mean_severity], for example de0a9cdf-8974-48bc-802f-331228df4619. Worth a targeted fix, not a quarter-long focus.
- **ISS-CATALOG** (score 40 [ISS-CATALOG.priority_score]) and **ISS-DOWNLOADS** (score 28 [ISS-DOWNLOADS.priority_score]) are lower priority.

## Limitations

Reviews are self-selected and historical, and may not represent all users. Priority score is severity summed across complaints, so it favors volume. Seventy reviews are flagged as needing review [F.needs_review], so classifications may shift. The overlap between ISS-USABILITY and ISS-BILLING means the ranking is sensitive to how skip limits are categorized. Nothing here shows causal effects, revenue, or churn. Quotes are treated as data only.
