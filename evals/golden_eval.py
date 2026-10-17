"""Compare the pipeline's saved predictions with the human golden-50 labels. No model calls.

    python -m evals.golden_eval --db work/full.sqlite

The golden reviews are part of the full corpus run, so their predictions already exist in the saved state.
The human labels (evals/golden_50_human.csv) are read only here, never by a prompt or a threshold.

Predeclared tolerances: sentiment counts as agreeing when |pred - human| <= 0.25 (one half-step on the
five-level sheet); severity reports exact agreement, within-1 agreement and mean absolute error.
Missing or quarantined predictions count as wrong.
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from pipeline import labels
from pipeline.common import ROOT, open_state, write_json
from pipeline.records import final_records, stored_label_config

HUMAN = ROOT / "evals" / "golden_50_human.csv"
OUT = ROOT / "evals" / "golden_eval.json"
SENTIMENT_TOLERANCE = 0.25


def macro_f1(pairs, classes):
    f1s = []
    for c in classes:
        tp = sum(h == c and p == c for h, p in pairs)
        fp = sum(h != c and p == c for h, p in pairs)
        fn = sum(h == c and p != c for h, p in pairs)
        if tp + fp + fn == 0:
            continue  # class absent from both - not part of the macro average
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return round(sum(f1s) / len(f1s), 4) if f1s else None


def evaluate(con):
    with open(HUMAN, newline="", encoding="utf-8") as f:
        human = {r["review_id"]: r for r in csv.DictReader(f)}
    cfg = stored_label_config(con)
    pred = {r["review_id"]: r for r in final_records(con, cfg) if r["review_id"] in human}
    cases, n = [], len(human)
    agree = Counter()
    sev_err, sent_err, sev_n, sent_n = 0, 0.0, 0, 0
    pairs = defaultdict(list)
    confusion = defaultdict(Counter)
    for rid, h in human.items():
        p = pred.get(rid)
        ok = p is not None and p["status"] == "completed"
        row = {"review_id": rid, "text": h["review_text"][:300], "human": {k: h[k] for k in
               ("topic", "intent", "severity", "sentiment", "needs_review")}, "notes": h.get("notes", "")}
        if not ok:
            row["prediction"] = {"status": p["status"] if p else "missing", "reason": p.get("reason") if p else None}
            for f in ("topic", "intent"):
                pairs[f].append((h[f], None))
            cases.append(row)
            continue
        hs, ps = int(h["severity"]), p["severity"]
        hsent, psent = float(h["sentiment"]), p["sentiment"]
        row["prediction"] = {k: p[k] for k in ("topic", "intent", "severity", "sentiment", "needs_review", "evidence_quote")}
        row["match"] = {"topic": h["topic"] == p["topic"], "intent": h["intent"] == p["intent"],
                        "severity": hs == ps, "sentiment": abs(hsent - psent) <= SENTIMENT_TOLERANCE,
                        "quote_is_substring": p["evidence_quote"] in h["review_text"]}
        for k, v in row["match"].items():
            agree[k] += v
        agree["severity_within_1"] += abs(hs - ps) <= 1
        sev_err += abs(hs - ps)
        sev_n += 1
        sent_err += abs(hsent - psent)
        sent_n += 1
        human_flag = h["needs_review"].lower() == "true"
        agree["needs_review_match"] += human_flag == p["needs_review"]
        for f in ("topic", "intent"):
            pairs[f].append((h[f], p[f]))
            confusion[f"{f}:{h[f]}"][p[f]] += 1
        cases.append(row)
    per_topic = Counter(h["topic"] for h in human.values())
    return {
        "label_config": cfg, "golden_reviews": n, "predicted_completed": sev_n,
        "agreement": {k: round(agree[k] / n, 4) for k in ("topic", "intent", "severity", "severity_within_1",
                                                          "sentiment", "quote_is_substring", "needs_review_match")},
        "macro_f1": {"topic": macro_f1(pairs["topic"], labels.TOPICS), "intent": macro_f1(pairs["intent"], labels.INTENTS)},
        "severity_mae": round(sev_err / sev_n, 4) if sev_n else None,
        "sentiment_mae": round(sent_err / sent_n, 4) if sent_n else None,
        "sentiment_tolerance": SENTIMENT_TOLERANCE,
        "human_ambiguous_cases": sum(1 for h in human.values() if h["needs_review"].lower() == "true"),
        "human_topic_counts": dict(per_topic),
        "confusion": {k: dict(v) for k, v in sorted(confusion.items())},
        "disagreements": [c for c in cases if not c.get("match") or not all(c["match"].values())],
        "cases": cases,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=ROOT / "work" / "full.sqlite")
    args = ap.parse_args()
    if not HUMAN.exists():
        raise SystemExit(f"{HUMAN} not found - label the sheet and run: python -m pipeline.golden export")
    rep = evaluate(open_state(args.db))
    write_json(OUT, rep)
    print({k: rep[k] for k in ("label_config", "golden_reviews", "predicted_completed", "agreement", "macro_f1",
                               "severity_mae", "sentiment_mae", "human_ambiguous_cases")})
    print(f"{len(rep['disagreements'])} reviews with at least one disagreement -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
