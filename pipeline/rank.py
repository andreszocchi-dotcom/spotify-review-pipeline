"""Stage 5 - Rank. Deterministic baseline ranking from saved records + issue membership. No model calls.

priority_score = severity_sum = complaint_count x mean_severity (exact integer arithmetic).
Order: descending score, then ascending issue ID. Means are exported with six decimals, half-up.

    python -m pipeline.rank --db work/state.sqlite --out outputs
"""

import argparse
import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from pipeline.common import DEFAULT_DB, ROOT, open_state
from pipeline.records import final_records

METRICS = ("complaint_count", "severity_sum", "mean_severity", "priority_score")


def load_membership(con):
    return con.execute("SELECT issue_id, review_id FROM membership ORDER BY issue_id, review_id").fetchall()


def compute_ranking(records, membership):
    severity = {r["review_id"]: r["severity"] for r in records if r["status"] == "completed"}
    agg = {}
    for issue_id, rid in membership:
        a = agg.setdefault(issue_id, [0, 0])
        a[0] += 1
        a[1] += severity[rid]
    ordered = sorted(agg.items(), key=lambda kv: (-kv[1][1], kv[0]))
    rows = []
    for rank, (issue_id, (count, sev_sum)) in enumerate(ordered, 1):
        mean = (Decimal(sev_sum) / Decimal(count)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        rows.append({"rank": rank, "issue_id": issue_id, "complaint_count": count, "severity_sum": sev_sum,
                     "mean_severity": f"{mean}", "priority_score": sev_sum})
    return rows


def claims_for(ranking):
    """One claim per issue-level number; the memo cites these claim IDs."""
    return [{"claim_id": f"{row['issue_id']}.{m}", "issue_id": row["issue_id"], "metric": m, "value": str(row[m])}
            for row in ranking for m in METRICS]


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def rank(con, out_dir):
    ranking = compute_ranking(final_records(con), load_membership(con))
    write_csv(Path(out_dir) / "ranking.csv", ranking,
              ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"])
    write_csv(Path(out_dir) / "claims.csv", claims_for(ranking), ["claim_id", "issue_id", "metric", "value"])
    return ranking


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--out", default=ROOT / "outputs")
    args = ap.parse_args()
    for row in rank(open_state(args.db), args.out):
        print(row)


if __name__ == "__main__":
    main()
