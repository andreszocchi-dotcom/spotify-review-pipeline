## Recommendation

Prioritize **ISS-USABILITY** next quarter. It ranks first in the full table with a priority score of 187 [ISS-USABILITY.priority_score] and a severity sum of 187 [ISS-USABILITY.severity_sum]. The focus should be unrequested auto-shuffle, skip and rewind limits, ad frequency, and layout changes.

## Evidence

- ISS-USABILITY has 66 complaints [ISS-USABILITY.complaint_count] with a mean severity of 2.833333 [ISS-USABILITY.mean_severity]. It accounts for 27.5 percent of complaints [F.ISS-USABILITY.share_of_complaints_pct], out of 240 complaint or cancellation reviews [F.complaint_or_cancellation].
- Example reviews: 0e5a2a0d-7f67-48a5-9edd-27064f670656 (a song plays that the user did not choose), af53cf35-c680-4ccb-b30c-cfd85bb61c57 (auto shuffle in the free tier), and 2aae0ce4-ae4a-46ce-b2fe-0d901eb23c06 (oversized icons and long scrolling to reach daily mixes).
- The analysis covers 500 reviews [F.total_reviews]. 29 reviews [F.cancellation_intent] express cancellation intent. This is stated intent, not observed churn.

## Alternatives considered

- **ISS-OTHER** has the most complaints, at 72 [ISS-OTHER.complaint_count], but its priority score is 142 [ISS-OTHER.priority_score] and its mean severity is only 1.972222 [ISS-OTHER.mean_severity]. It also names no specific feature (e.g. 1db044db-d184-4335-877c-d8fc364b282e, "I hate application"), so there is nothing concrete to build against. I would not fund it directly.
- **ISS-PLAYBACK** ranks third with a score of 123 [ISS-PLAYBACK.priority_score] from 36 complaints [ISS-PLAYBACK.complaint_count]. Its mean severity of 3.416667 [ISS-PLAYBACK.mean_severity] is high among the larger issues, and reviews cite crashes after updates (4a806587-0dde-4fb4-b4f1-f5c7d197c927). It is the strongest runner-up, and reliability fixes could run in parallel.
- **ISS-BILLING** has a score of 102 [ISS-BILLING.priority_score] from 35 complaints [ISS-BILLING.complaint_count]. Reviews describe features locked behind Premium (d146397f-4a94-4980-be00-ae9212eca3a7). This overlaps with the ISS-USABILITY skip and shuffle complaints, so those decisions are partly a monetization trade-off and not purely a usability one.
- **ISS-ACCESS** has 9 complaints [ISS-ACCESS.complaint_count] but a mean severity of 4.000000 [ISS-ACCESS.mean_severity]. **ISS-DOWNLOADS** has 7 complaints [ISS-DOWNLOADS.complaint_count] and a mean severity of 4.142857 [ISS-DOWNLOADS.mean_severity]. Both are severe per review but small in volume, so they suit a low-cost targeted fix and not a quarter-long focus. **ISS-CATALOG** has 15 complaints [ISS-CATALOG.complaint_count] and a score of 41 [ISS-CATALOG.priority_score].

## Limitations

- Reviews are self-selected and historical, so they may not represent all users.
- 70 reviews [F.needs_review] were flagged as needing review, which adds classification uncertainty.
- The priority score is severity-weighted volume. It is not a measure of revenue, churn, or causal impact.
- ISS-USABILITY and ISS-BILLING overlap in theme, so category boundaries are imperfect.
- Quotes are treated as data only.
