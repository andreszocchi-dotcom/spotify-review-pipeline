"""Load processed pipeline outputs into the dashboard database (Postgres in production, SQLite locally).

Reads the pipeline's saved state and output files - no model calls - and (re)creates these tables:
records, ranking, issues, membership, claims, facts, memo, monthly, run_info.

    python -m dashboard.load --db work/state.sqlite --outputs outputs/full --database-url "$DATABASE_URL"
    python -m dashboard.load --db work/dev500.sqlite --outputs outputs/dev500 --database-url sqlite:///work/dashboard.sqlite
"""

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, text

from dashboard.db import normalize_url
from pipeline.common import open_state
from pipeline.records import final_records, stored_label_config

DDL = [
    """CREATE TABLE records (review_id TEXT PRIMARY KEY, status TEXT NOT NULL, reason TEXT, topic TEXT, intent TEXT,
        severity INTEGER, sentiment REAL, needs_review BOOLEAN, evidence_quote TEXT, cache_source_id TEXT,
        review_rating TEXT, review_timestamp TEXT, app_version TEXT, issue_id TEXT)""",
    "CREATE INDEX records_issue ON records (issue_id, severity)",
    "CREATE INDEX records_topic ON records (topic, intent)",
    """CREATE TABLE ranking (rank INTEGER PRIMARY KEY, issue_id TEXT NOT NULL, complaint_count INTEGER NOT NULL,
        severity_sum INTEGER NOT NULL, mean_severity TEXT NOT NULL, priority_score INTEGER NOT NULL)""",
    """CREATE TABLE issues (issue_id TEXT PRIMARY KEY, topic TEXT NOT NULL, name TEXT NOT NULL, summary TEXT NOT NULL,
        representative_review_ids TEXT NOT NULL)""",
    "CREATE TABLE claims (claim_id TEXT PRIMARY KEY, issue_id TEXT NOT NULL, metric TEXT NOT NULL, value TEXT NOT NULL)",
    "CREATE TABLE facts (fact_id TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE memo (id INTEGER PRIMARY KEY, markdown TEXT NOT NULL, recommended_issue_id TEXT NOT NULL, checks TEXT NOT NULL, config TEXT NOT NULL)",
    "CREATE TABLE monthly (month TEXT NOT NULL, topic TEXT NOT NULL, complaints INTEGER NOT NULL, reviews INTEGER NOT NULL, PRIMARY KEY (month, topic))",
    "CREATE TABLE run_info (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
]
TABLES = ["records", "ranking", "issues", "claims", "facts", "memo", "monthly", "run_info"]


def load(state_db, outputs, url, quote_max=300):
    outputs = Path(outputs)
    con = open_state(state_db)
    records = final_records(con, stored_label_config(con))
    src = {rid: (rating, ts, ver) for rid, rating, ts, ver in
           con.execute("SELECT review_id, review_rating, review_timestamp, app_version FROM reviews")}
    issue_of = dict((rid, iid) for iid, rid in con.execute("SELECT issue_id, review_id FROM membership"))
    ranking = [row for row in _csv(outputs / "ranking.csv")]
    claims = [row for row in _csv(outputs / "claims.csv")]
    issues = json.loads((outputs / "issues.json").read_text(encoding="utf-8"))
    memo_inputs = json.loads((outputs / "memo_inputs.json").read_text(encoding="utf-8"))
    checks = json.loads((outputs / "memo_checks.json").read_text(encoding="utf-8"))
    memo_md = (outputs / "memo.md").read_text(encoding="utf-8")
    run = json.loads((outputs / "run_summary.json").read_text(encoding="utf-8")) if (outputs / "run_summary.json").exists() else {}
    verify = json.loads((outputs / "verify_report.json").read_text(encoding="utf-8")) if (outputs / "verify_report.json").exists() else {}

    monthly, totals = Counter(), Counter()
    for r in records:
        month = src[r["review_id"]][1][:7]
        totals[month] += 1
        if r["status"] == "completed" and r["intent"] in ("complaint", "cancellation"):
            monthly[(month, r["topic"])] += 1

    engine = create_engine(normalize_url(url))
    with engine.begin() as db:
        for t in TABLES:
            db.execute(text(f"DROP TABLE IF EXISTS {t}"))
        for ddl in DDL:
            db.execute(text(ddl))
        rows = []
        for r in records:
            rating, ts, ver = src[r["review_id"]]
            rows.append({"review_id": r["review_id"], "status": r["status"], "reason": r.get("reason"),
                         "topic": r.get("topic"), "intent": r.get("intent"), "severity": r.get("severity"),
                         "sentiment": r.get("sentiment"), "needs_review": r.get("needs_review"),
                         "evidence_quote": (r.get("evidence_quote") or "")[:quote_max] or None,
                         "cache_source_id": r.get("cache_source_id"), "review_rating": rating,
                         "review_timestamp": ts, "app_version": ver or None, "issue_id": issue_of.get(r["review_id"])})
        ins = text("""INSERT INTO records VALUES (:review_id, :status, :reason, :topic, :intent, :severity, :sentiment,
            :needs_review, :evidence_quote, :cache_source_id, :review_rating, :review_timestamp, :app_version, :issue_id)""")
        for i in range(0, len(rows), 5000):
            db.execute(ins, rows[i:i + 5000])
        db.execute(text("INSERT INTO ranking VALUES (:rank, :issue_id, :complaint_count, :severity_sum, :mean_severity, :priority_score)"),
                   [{**r, "rank": int(r["rank"])} for r in ranking])
        db.execute(text("INSERT INTO issues VALUES (:issue_id, :topic, :name, :summary, :reps)"),
                   [{"issue_id": i["issue_id"], "topic": i["topic"], "name": i["name"], "summary": i["summary"],
                     "reps": json.dumps(i["representative_review_ids"])} for i in issues])
        db.execute(text("INSERT INTO claims VALUES (:claim_id, :issue_id, :metric, :value)"), claims)
        db.execute(text("INSERT INTO facts VALUES (:fact_id, :value)"),
                   [{"fact_id": f["fact_id"], "value": str(f["value"])} for f in memo_inputs["facts"]])
        db.execute(text("INSERT INTO memo VALUES (1, :md, :rec, :checks, :config)"),
                   {"md": memo_md, "rec": checks["recommended_issue_id"], "checks": json.dumps(checks),
                    "config": memo_inputs.get("config", "")})
        monthly_rows = [{"month": m, "topic": t, "complaints": n, "reviews": totals[m]} for (m, t), n in sorted(monthly.items())]
        if monthly_rows:
            db.execute(text("INSERT INTO monthly VALUES (:month, :topic, :complaints, :reviews)"), monthly_rows)
        info = {"input_sha256": con.execute("SELECT value FROM meta WHERE key='input_sha256'").fetchone()[0],
                "run_id": run.get("run_id", ""), "wall_seconds": str(run.get("wall_seconds", "")),
                "calls_by_role": json.dumps(run.get("calls_by_role", {})),
                "verify": json.dumps({k: verify.get(k) for k in ("sampled", "verified", "agreement", "severity_mae", "disagreements")}),
                "label_config": records and next((r["label_config"] for r in records if r["status"] == "completed"), "") or ""}
        db.execute(text("INSERT INTO run_info VALUES (:k, :v)"), [{"k": k, "v": v} for k, v in info.items()])
    return len(records)


def _csv(path):
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="pipeline state database")
    ap.add_argument("--outputs", required=True, help="pipeline output folder (ranking.csv, issues.json, memo.md ...)")
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = ap.parse_args()
    if not args.database_url:
        raise SystemExit("set --database-url or DATABASE_URL")
    print(f"loaded {load(args.db, args.outputs, args.database_url):,} records")


if __name__ == "__main__":
    main()
