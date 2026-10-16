## Recommendation

Put the next quarter's effort on **ISS-USABILITY** (playlist loss, shuffle, and playback control failures). It has the highest priority score, [ISS-USABILITY.priority_score], which is above ISS-OTHER's [ISS-OTHER.priority_score]. Its mean severity is [ISS-USABILITY.mean_severity], and it accounts for a share of complaints of [F.ISS-USABILITY.share_of_complaints_pct]%. As a secondary workstream, investigate ISS-BILLING (see Alternatives).

## Evidence

- The classified set has [F.total_reviews] reviews, of which [F.complaint_or_cancellation] are complaints or cancellation mentions [F.complaint_or_cancellation]. Nothing was quarantined [F.quarantined].
- ISS-USABILITY has a complaint count of [ISS-USABILITY.complaint_count] and a severity sum of [ISS-USABILITY.severity_sum].
- Example reviews show the severity of the harm. Review ee11e1df-cb73-4c3a-b5e8-7268c7872b01 describes a playlist of hundreds of songs that "just vanished". Review 9eb843c6-ab2d-459d-8507-5b8128279fcc reports skip and replay controls not working. Review 7a9422f5-7266-4f53-adf3-7cc65803e8bf reports shuffle repeating the same artist.
- Playlist loss is data loss, not mere annoyance, and is likely to erode trust in the product.

## Alternatives considered

- **ISS-OTHER** ranks second on count ([ISS-OTHER.complaint_count]) and share ([F.ISS-OTHER.share_of_complaints_pct]%). Its mean severity is low ([ISS-OTHER.mean_severity]) and it is a catch-all of vague complaints (e.g. 1c4d38cb-9e3f-4f46-99d4-9b4d4880492f, 21ddfe12-8433-4bad-b0f8-e7f605c056ae). It is not actionable until it is broken down further.
- **ISS-BILLING** has a priority score of [ISS-BILLING.priority_score] and a mean severity of [ISS-BILLING.mean_severity]. Reviews such as ff7a2f97-2603-4e0e-95c9-29fa03a803a3 and 70c10706-cb1c-4623-9c21-bf303e1e6ebe report charges after cancelling. This is a strong candidate for a focused cancellation-flow audit. Cancellation intent appears in [F.cancellation_intent] reviews, but that is stated intent, not observed churn.
- **ISS-PLAYBACK** has a priority score of [ISS-PLAYBACK.priority_score] and a higher mean severity of [ISS-PLAYBACK.mean_severity]. Crashes (73724807-3061-4a00-86fe-64065dbd8d74) are serious. It may share root causes with ISS-USABILITY and could be bundled with it.
- **ISS-ACCESS** has the highest mean severity ([ISS-ACCESS.mean_severity]) but a small volume ([ISS-ACCESS.complaint_count]). Lockouts that wipe liked songs (55123d02-711d-4e41-b644-06e2c3c4db18) warrant a targeted fix.
- **ISS-CATALOG**, **ISS-DOWNLOADS**, and **ISS-SUPPORT** are lower priority ([ISS-CATALOG.priority_score], [ISS-DOWNLOADS.priority_score], [ISS-SUPPORT.priority_score]).

## Limitations

Reviews are self-selected and historical, so they may not represent all users or current app behavior. Classification is automated, and [F.needs_review] reviews were flagged as needing review. The priority score reflects volume and severity as classified, not revenue, churn, or causal impact. Cancellation language is stated intent only. Quotes are treated as data, not instructions. ISS-OTHER's size suggests that taxonomy gaps may hide additional themes.
