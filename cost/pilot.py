"""PAID: run the real 100-review pilot, cold then warm. Makes Jev and Claude API calls.

    python -m cost.pilot --confirm-paid

Cold run: empty result cache (fresh database), one worker, full pipeline on data/cost_100.csv unchanged.
Warm run: the same command against the saved database - enrichment must make zero new calls, and
downstream stages reuse their cached artifacts. Evidence is written to cost/ for offline replay
(python -m cost.calculator), which never calls an API.
"""

import argparse
import csv
import json
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

from pipeline.common import DATA, ROOT, file_sha, open_state, write_json
from pipeline.export import calls, write_jsonl
from pipeline.records import final_records
from pipeline.run import parser, run_pipeline

COST = ROOT / "cost"
PILOT_CSV = DATA / "cost_100.csv"
DB = ROOT / "work" / "pilot.sqlite"
LIMITS = {"jev_token_cap": 250_000, "usd_cap": 0.50, "workers": 1, "verify_rate": 0.2, "verify_max": 20}


def run_once(kind):
    args = parser().parse_args([
        "--input", str(PILOT_CSV), "--db", str(DB), "--out", str(COST / "runs" / kind),
        "--workers", str(LIMITS["workers"]), "--jev-token-cap", str(LIMITS["jev_token_cap"]),
        "--usd-cap", str(LIMITS["usd_cap"]), "--verify-rate", str(LIMITS["verify_rate"]),
        "--verify-max", str(LIMITS["verify_max"]), "--run-id", f"pilot-{kind}"])
    t0 = time.perf_counter()
    summary = run_pipeline(args)
    summary["end_to_end_wall_seconds"] = round(time.perf_counter() - t0, 3)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--confirm-paid", action="store_true", help="required: this command spends real API credit")
    if not ap.parse_args().confirm_paid:
        sys.exit("Refusing to make paid calls without --confirm-paid. For offline replay run: python -m cost.calculator")

    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest["files"]["cost_100.csv"]["sha256"]
    actual = file_sha(PILOT_CSV)
    if actual != expected:
        sys.exit(f"cost_100.csv checksum mismatch: {actual} != {expected}")

    for p in DB.parent.glob(DB.name + "*"):  # cold run = empty result cache
        p.unlink()
    shutil.rmtree(COST / "runs", ignore_errors=True)
    runs = {"cold": run_once("cold"), "warm": run_once("warm")}

    con = open_state(DB)
    ids = [r[0] for r in con.execute("SELECT review_id FROM reviews ORDER BY row_idx")]
    distinct = con.execute("SELECT COUNT(DISTINCT text_sha256) FROM reviews WHERE is_empty = 0").fetchone()[0]
    records = final_records(con)
    write_jsonl(COST / "pilot_records.jsonl", records)

    pilot_calls = []
    for c in calls(con):
        c["pilot_run"] = "warm" if c["run_id"].startswith("pilot-warm") else "cold"
        pilot_calls.append(c)
    write_jsonl(COST / "pilot_calls.jsonl", pilot_calls)

    # usage.csv: billed units per (run, stage, provider, model, item); every unit maps to call rows above.
    usage = defaultdict(lambda: [0, 0])
    for c in pilot_calls:
        for item in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            if c.get(item):
                u = usage[(c["pilot_run"], c["role"], c["provider"], c["model"], item)]
                u[0] += c[item]
        usage[(c["pilot_run"], c["role"], c["provider"], c["model"], "attempts")][0] += 1
        usage[(c["pilot_run"], c["role"], c["provider"], c["model"], "attempts")][1] += c["outcome"] == "failed"
    with open(COST / "usage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["pilot_run", "stage", "provider", "model", "item", "units", "failed_attempts", "source"])
        for (run, stage, prov, model, item), (units, failed) in sorted(usage.items()):
            w.writerow([run, stage, prov, model, item, units, failed if item == "attempts" else "",
                        f"pilot_calls.jsonl where pilot_run={run} and role={stage}"])

    status = defaultdict(int)
    for r in records:
        status[r["status"]] += 1
    write_json(COST / "pilot_measurements.json", {
        "input": "data/cost_100.csv", "input_sha256": actual, "review_ids": ids, "rows": len(ids),
        "distinct_nonempty_texts": distinct, "status_counts": dict(status), "limits": LIMITS, "runs": runs,
        "result_cache_hits": {k: distinct - runs[k]["stages"]["enrich"].get("pending_at_start", 0) for k in runs},
    })
    print(f"\nPilot evidence saved under {COST}. Offline replay: python -m cost.calculator")


if __name__ == "__main__":
    main()
