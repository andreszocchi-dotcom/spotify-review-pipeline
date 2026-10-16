"""One final record per source review ID, derived from saved state with no model calls.

* empty text                       -> quarantined, reason empty_review_text
* canonical text with a result     -> completed (the record whose call produced the labels)
* duplicate text of a completed one -> completed, with cache_source_id = that canonical review
* text quarantined by enrichment   -> quarantined with the enrichment reason (duplicates inherit it)
* text never processed             -> quarantined, reason not_processed (pending work is not a success)
"""

import json

from pipeline import labels


def final_records(con, label_config=labels.LABEL_CONFIG):
    results = {row[0]: row for row in con.execute(
        """SELECT text_sha256, source_review_id, topic, intent, sentiment, severity, entities, evidence_quote,
                  needs_review FROM results WHERE label_config = ?""", (label_config,))}
    quarantine = {rid: (reason, attempts) for rid, reason, attempts in
                  con.execute("SELECT review_id, reason, attempts FROM quarantine")}
    out = []
    for rid, src_sha, text, tsha, empty, canonical in con.execute(
            "SELECT review_id, source_sha256, review_text, text_sha256, is_empty, canonical_id FROM reviews ORDER BY row_idx"):
        base = {"review_id": rid, "source_sha256": src_sha}
        if empty:
            out.append({**base, "status": "quarantined", "reason": "empty_review_text"})
            continue
        res = results.get(tsha)
        if res is None:
            reason = quarantine.get(canonical, ("not_processed", 0))[0]
            out.append({**base, "status": "quarantined", "reason": reason})
            continue
        _, source_id, topic, intent, sentiment, severity, entities, quote, needs_review = res
        rec = {**base, "status": "completed", "topic": topic, "intent": intent, "sentiment": sentiment,
               "severity": severity, "entities": json.loads(entities), "evidence_quote": quote,
               "needs_review": bool(needs_review), "label_config": label_config}
        if source_id != rid:
            rec["cache_source_id"] = source_id
        out.append(rec)
    return out


def stored_label_config(con):
    """The current LABEL_CONFIG if this database has results under it, else the one with the most results."""
    counts = dict(con.execute("SELECT label_config, COUNT(*) FROM results GROUP BY label_config"))
    if labels.LABEL_CONFIG in counts or not counts:
        return labels.LABEL_CONFIG
    return max(counts, key=counts.get)


def is_complaint(rec):
    return rec["status"] == "completed" and rec["intent"] in ("complaint", "cancellation")
