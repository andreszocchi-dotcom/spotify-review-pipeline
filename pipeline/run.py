"""Orchestrator: ingest -> enrich -> verify -> group -> rank -> memo for one input CSV.

Code decides the order, budgets, retries and stop conditions; models only do the language tasks.
Each stage saves its handoff (SQLite state + files under --out) before the next starts, and the
run summary records per-stage wall-clock time, calls and token usage.

    python -m pipeline.run --input data/cost_100.csv --db work/pilot.sqlite --out outputs/pilot \
        --jev-token-cap 300000 --usd-cap 1.00
"""

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from pipeline import enrich, group, memo, rank, verify
from pipeline.common import ROOT, open_state, write_json
from pipeline.ingest import ingest


def call_stats(con, run_ids):
    q = ",".join("?" * len(run_ids))
    rows = con.execute(f"""SELECT role, COUNT(*), SUM(outcome='failed'), COALESCE(SUM(input_tokens),0),
        COALESCE(SUM(output_tokens),0) FROM calls WHERE run_id IN ({q}) GROUP BY role""", run_ids).fetchall()
    return {r[0]: {"attempts": r[1], "failed": r[2], "input_tokens": r[3], "output_tokens": r[4]} for r in rows}


def run_pipeline(a):
    load_dotenv(ROOT / ".env")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    run_id = a.run_id or f"run-{stamp}"
    stages, t_all = {}, time.perf_counter()

    def timed(name, fn):
        t = time.perf_counter()
        result = fn()
        stages[name] = {"seconds": round(time.perf_counter() - t, 3)}
        print(f"[{name}] {stages[name]['seconds']}s")
        return result

    report = timed("ingest", lambda: ingest(Path(a.input).resolve(), a.db))
    write_json(out / "ingestion_report.json", report)
    con = open_state(a.db)

    eargs = argparse.Namespace(db=a.db, workers=a.workers, token_cap=a.jev_token_cap, limit=a.enrich_limit,
                               stop_after_batches=a.stop_after_batches, retry_failed=False, phase=None,
                               timeout=30.0, run_id=f"{run_id}-enrich")
    esum = timed("enrich", lambda: asyncio.run(enrich.run(eargs)))
    stages["enrich"].update(esum)
    if a.stop_after_batches or esum["stop_reason"] != "done":
        print(f"enrichment stopped: {esum['stop_reason']}; later stages not run")
        return finish(con, a, run_id, stages, t_all, out)

    con = open_state(a.db)
    picked, sent, failures = timed("verify", lambda: verify.verify(con, f"{run_id}-verify", "initial",
                                                                    a.verify_rate, a.verify_max, a.usd_cap))
    vrep = verify.report(con, picked, failures)
    write_json(out / "verify_report.json", vrep)
    stages["verify"].update({"sampled": len(picked), "sent_to_model": sent, "failures": len(failures)})

    issues, gcalls = timed("group", lambda: group.group(con, f"{run_id}-group", "initial", a.usd_cap))
    write_json(out / "issues.json", issues)
    rank.write_csv(out / "membership.csv", [{"issue_id": i, "review_id": r} for i, r in rank.load_membership(con)],
                   ["issue_id", "review_id"])
    stages["group"].update({"issues": len(issues), "model_calls": gcalls})

    ranking = timed("rank", lambda: rank.rank(con, out))
    stages["rank"].update({"issues_ranked": len(ranking)})

    m, pack, checks, key, mcalls = timed("memo", lambda: memo.write_memo(con, f"{run_id}-memo", "initial", a.usd_cap))
    (out / "memo.md").write_text(m["memo_markdown"] + "\n", encoding="utf-8")
    write_json(out / "memo_inputs.json", {"input_sha256": key, "config": memo.MEMO_CONFIG, **pack})
    write_json(out / "memo_checks.json", {"recommended_issue_id": m["recommended_issue_id"], **checks})
    stages["memo"].update({"model_calls": mcalls, "recommended_issue_id": m["recommended_issue_id"]})
    return finish(con, a, run_id, stages, t_all, out)


def finish(con, a, run_id, stages, t_all, out):
    run_ids = [f"{run_id}-{s}" for s in ("enrich", "verify", "group", "memo")]
    summary = {"run_id": run_id, "input": str(a.input), "db": str(a.db),
               "wall_seconds": round(time.perf_counter() - t_all, 3), "stages": stages,
               "calls_by_role": call_stats(con, run_ids),
               "limits": {"jev_token_cap": a.jev_token_cap, "usd_cap": a.usd_cap, "workers": a.workers,
                          "verify_rate": a.verify_rate, "verify_max": a.verify_max}}
    write_json(out / "run_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("run_id", "wall_seconds", "calls_by_role")}, indent=2))
    return summary


def parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--jev-token-cap", type=int, default=None)
    ap.add_argument("--usd-cap", type=float, default=None, help="cumulative Anthropic spend cap for this database")
    ap.add_argument("--verify-rate", type=float, default=0.2)
    ap.add_argument("--verify-max", type=int, default=2000)
    ap.add_argument("--enrich-limit", type=int, default=None)
    ap.add_argument("--stop-after-batches", type=int, default=None)
    ap.add_argument("--run-id", default=None)
    return ap


if __name__ == "__main__":
    run_pipeline(parser().parse_args())
