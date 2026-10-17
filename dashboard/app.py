"""Dashboard backend: serves processed review data from the database. Read-only; no model calls.

    DATABASE_URL=sqlite:///work/dashboard.sqlite uvicorn dashboard.app:app --reload
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

from dashboard.db import normalize_url

STATIC = Path(__file__).resolve().parent / "static"
engine = create_engine(normalize_url(os.environ.get("DATABASE_URL", "sqlite:///work/dashboard.sqlite")), pool_pre_ping=True)
app = FastAPI(title="Spotify review insights")


def rows(sql, **params):
    with engine.connect() as db:
        return [dict(r._mapping) for r in db.execute(text(sql), params)]


@app.get("/api/summary")
def summary():
    info = {r["key"]: r["value"] for r in rows("SELECT key, value FROM run_info")}
    run = {**{k: v for k, v in info.items() if k != "summary"},
           "calls_by_role": json.loads(info.get("calls_by_role", "{}")), "verify": json.loads(info.get("verify", "{}"))}
    if "summary" in info:  # precomputed by dashboard.load
        return {**json.loads(info["summary"]), "run": run}
    status = {r["status"]: r["n"] for r in rows("SELECT status, COUNT(*) AS n FROM records GROUP BY status")}
    intents = {r["intent"]: r["n"] for r in rows(
        "SELECT intent, COUNT(*) AS n FROM records WHERE status='completed' GROUP BY intent")}
    topics = rows("""SELECT topic, COUNT(*) AS n,
        SUM(CASE WHEN intent IN ('complaint','cancellation') THEN 1 ELSE 0 END) AS complaints
        FROM records WHERE status='completed' GROUP BY topic ORDER BY n DESC""")
    reasons = rows("SELECT reason, COUNT(*) AS n FROM records WHERE status='quarantined' GROUP BY reason")
    info = {r["key"]: r["value"] for r in rows("SELECT key, value FROM run_info")}
    needs = rows("SELECT COUNT(*) AS n FROM records WHERE status='completed' AND needs_review")[0]["n"]
    cached = rows("SELECT COUNT(*) AS n FROM records WHERE cache_source_id IS NOT NULL")[0]["n"]
    return {"status": status, "intents": intents, "topics": topics, "quarantine_reasons": reasons,
            "needs_review": needs, "cache_reused": cached,
            "run": {**info, "calls_by_role": json.loads(info.get("calls_by_role", "{}")),
                    "verify": json.loads(info.get("verify", "{}"))}}


@app.get("/api/ranking")
def ranking():
    return rows("""SELECT r.rank, r.issue_id, i.name, i.summary, r.complaint_count, r.severity_sum,
        r.mean_severity, r.priority_score FROM ranking r LEFT JOIN issues i ON i.issue_id = r.issue_id ORDER BY r.rank""")


@app.get("/api/issues/{issue_id}")
def issue(issue_id: str):
    found = rows("SELECT * FROM issues WHERE issue_id = :i", i=issue_id)
    if not found:
        raise HTTPException(404, "unknown issue")
    it = found[0]
    reps = json.loads(it["representative_review_ids"])
    it["representative"] = rows(
        "SELECT review_id, severity, intent, evidence_quote, review_rating, review_timestamp FROM records "
        "WHERE review_id IN (" + ",".join(f":r{n}" for n in range(len(reps))) + ")", **{f"r{n}": r for n, r in enumerate(reps)}) if reps else []
    it["severity_mix"] = rows("SELECT severity, COUNT(*) AS n FROM records WHERE issue_id = :i GROUP BY severity ORDER BY severity", i=issue_id)
    it["claims"] = rows("SELECT claim_id, metric, value FROM claims WHERE issue_id = :i", i=issue_id)
    return it


@app.get("/api/reviews")
def reviews(issue_id: str | None = None, severity: int | None = None, limit: int = Query(25, le=100), offset: int = 0):
    where, params = ["status = 'completed'"], {"limit": limit, "offset": offset}
    if issue_id:
        where.append("issue_id = :issue_id")
        params["issue_id"] = issue_id
    if severity:
        where.append("severity = :severity")
        params["severity"] = severity
    sql = (f"SELECT review_id, topic, intent, severity, sentiment, needs_review, evidence_quote, review_rating, "
           f"review_timestamp, cache_source_id FROM records WHERE {' AND '.join(where)} "
           f"ORDER BY severity DESC, review_id LIMIT :limit OFFSET :offset")
    return rows(sql, **params)


@app.get("/api/reviews/{review_id}")
def review(review_id: str):
    found = rows("SELECT * FROM records WHERE review_id = :r", r=review_id)
    if not found:
        raise HTTPException(404, "unknown review")
    return found[0]


@app.get("/api/recommendation")
def recommendation():
    m = rows("SELECT markdown, recommended_issue_id, checks, config FROM memo WHERE id = 1")
    if not m:
        raise HTTPException(404, "no memo loaded")
    m = m[0]
    return {**m, "checks": json.loads(m["checks"]),
            "claims": rows("SELECT claim_id, issue_id, metric, value FROM claims ORDER BY claim_id"),
            "facts": rows("SELECT fact_id, value FROM facts ORDER BY fact_id")}


@app.get("/api/trends")
def trends():
    return rows("SELECT month, topic, complaints, reviews FROM monthly ORDER BY month, topic")


@app.get("/api/health")
def health():
    return {"ok": True, "records": rows("SELECT COUNT(*) AS n FROM records")[0]["n"]}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
