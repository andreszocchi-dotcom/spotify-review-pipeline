"""Write the standardized grading/ export (GRADING_CONTRACT.md) from saved state. No model calls.

    python -m pipeline.export --db work/state.sqlite --out grading --gzip
    python -m pipeline.export --db work/state.sqlite --checkpoint before --out grading
"""

import argparse
import gzip
import json
import shutil
from pathlib import Path

from pipeline.common import DEFAULT_DB, ROOT, open_state, write_json
from pipeline.rank import claims_for, compute_ranking, load_membership, write_csv
from pipeline.records import final_records

CALL_FIELDS = ("request_id", "role", "review_ids", "model", "phase", "outcome", "label_config",
               "input_tokens", "output_tokens", "provider", "settings", "cache_read_input_tokens",
               "cache_creation_input_tokens", "attempt", "error", "run_id", "started_at", "seconds")


def calls(con, run_prefix=None):
    sql = f"SELECT {', '.join(CALL_FIELDS)} FROM calls"
    params = ()
    if run_prefix:
        sql += " WHERE run_id LIKE ?"
        params = (run_prefix + "%",)
    for row in con.execute(sql + " ORDER BY started_at", params):
        c = dict(zip(CALL_FIELDS, row))
        c["review_ids"] = json.loads(c["review_ids"])
        c["settings"] = json.loads(c["settings"])
        if c["input_tokens"] is None or c["output_tokens"] is None:
            # The provider returned no usage (connection error before any response). The contract format needs
            # integers, so these export as 0 and say so; the state database keeps them NULL.
            c["usage_source"] = "none_returned: failed before any provider response; billed usage unknown, exported as 0"
            c["input_tokens"] = c["input_tokens"] or 0
            c["output_tokens"] = c["output_tokens"] or 0
        else:
            c["usage_source"] = "provider_response"
        yield c


def write_jsonl(path, rows, gz=False):
    path = Path(str(path) + (".gz" if gz else ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if gz else open
    tmp = path.with_name(path.name + ".tmp")
    with opener(tmp, "wt", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(path)
    return path


def completed_ids(con):
    return sorted(r["review_id"] for r in final_records(con) if r["status"] == "completed")


def export(con, out, gz=False, ingestion_json=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    records = final_records(con)
    n = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    sha = con.execute("SELECT value FROM meta WHERE key = 'input_sha256'").fetchone()[0]
    write_json(out / "run.json", {"version": "a5-audit-v1", "analysis_count": n, "analysis_sha256": sha,
                                  "classification_input_fields": ["review_text"], "allow_multi_issue": False})
    if ingestion_json and Path(ingestion_json).resolve() != (out / "ingestion.json").resolve():
        shutil.copy(ingestion_json, out / "ingestion.json")
    write_jsonl(out / "records.jsonl", records, gz)
    membership = load_membership(con)
    write_csv(out / "membership.csv", [{"issue_id": i, "review_id": r} for i, r in membership], ["issue_id", "review_id"])
    ranking = compute_ranking(records, membership)
    write_csv(out / "ranking.csv", ranking, ["rank", "issue_id", "complaint_count", "severity_sum", "mean_severity", "priority_score"])
    write_csv(out / "claims.csv", claims_for(ranking), ["claim_id", "issue_id", "metric", "value"])
    write_jsonl(out / "calls.jsonl", calls(con), gz)
    status = {}
    for r in records:
        status[r["status"]] = status.get(r["status"], 0) + 1
    return status


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--out", default=ROOT / "grading")
    ap.add_argument("--gzip", action="store_true")
    ap.add_argument("--ingestion-json", default=None, help="helper-produced full-file profile to include")
    ap.add_argument("--checkpoint", choices=["before", "after"], help="only write checkpoint_<x>.json")
    args = ap.parse_args()
    con = open_state(args.db)
    if args.checkpoint:
        ids = completed_ids(con)
        write_json(Path(args.out) / f"checkpoint_{args.checkpoint}.json", {"completed_ids": ids})
        print(f"checkpoint_{args.checkpoint}.json: {len(ids)} completed IDs")
        return
    print(export(con, args.out, args.gzip, args.ingestion_json))


if __name__ == "__main__":
    main()
