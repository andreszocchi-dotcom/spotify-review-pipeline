"""Stage 1 - Prepare. No model calls.

Reads every row of an input CSV, preserves IDs and source values, hashes each row,
profiles quality, finds exact duplicate texts, quarantines empty texts, and builds
the pending-work queue (one entry per distinct nonempty text).

    python -m pipeline.ingest --input data/spotify_reviews_18months.csv
"""

import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone

from pipeline.common import DATA, DEFAULT_DB, ROOT, connect, csv_rows, file_sha, row_sha, text_sha, write_json

SCHEMA = """
DROP TABLE IF EXISTS reviews;
CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    row_idx INTEGER NOT NULL,
    source_sha256 TEXT NOT NULL,
    review_text TEXT NOT NULL,
    review_rating TEXT NOT NULL,
    review_likes TEXT NOT NULL,
    app_version TEXT NOT NULL,
    review_timestamp TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    is_empty INTEGER NOT NULL,
    canonical_id TEXT            -- first review_id with this exact text (NULL for empty texts)
);
"""


def ingest(input_path, db_path):
    started = time.time()
    con = connect(db_path)
    con.executescript(SCHEMA)

    counts = Counter()
    ratings, months = Counter(), Counter()
    first_by_text = {}
    rows = []
    for idx, row in enumerate(csv_rows(input_path)):
        text = row["review_text"]
        empty = not text.strip()
        tsha = text_sha(text)
        canonical = None if empty else first_by_text.setdefault(tsha, row["review_id"])
        counts["records"] += 1
        counts["empty_review_text"] += empty
        counts["missing_app_version"] += not row["app_version"].strip()
        counts["exact_duplicate_text_rows"] += (not empty) and canonical != row["review_id"]
        ratings[row["review_rating"]] += 1
        months[row["review_timestamp"][:7]] += 1
        rows.append((row["review_id"], idx, row_sha(row), text, row["review_rating"], row["review_likes"],
                     row["app_version"], row["review_timestamp"], tsha, int(empty), canonical))
        if len(rows) >= 20000:
            con.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
            rows.clear()
    try:
        con.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    except Exception as e:  # the PRIMARY KEY rejects repeated review IDs
        raise SystemExit(f"Ingestion failed: {e}")
    con.commit()

    # Empty texts are quarantined now; they never reach a model.
    con.execute("""CREATE TABLE IF NOT EXISTS quarantine (
        review_id TEXT PRIMARY KEY, reason TEXT NOT NULL, attempts INTEGER NOT NULL, stage TEXT NOT NULL)""")
    con.execute("DELETE FROM quarantine WHERE reason = 'empty_review_text'")
    con.execute("""INSERT INTO quarantine SELECT review_id, 'empty_review_text', 0, 'ingest'
                   FROM reviews WHERE is_empty = 1""")
    con.commit()

    distinct = con.execute("SELECT COUNT(DISTINCT text_sha256) FROM reviews WHERE is_empty = 0").fetchone()[0]
    dup_ids = counts["records"] - con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    nonempty = counts["records"] - counts["empty_review_text"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_path": str(input_path),
        "input_bytes": input_path.stat().st_size,
        "input_sha256": file_sha(input_path),
        "records": counts["records"],
        "duplicate_review_ids": dup_ids,
        "empty_review_text_quarantined": counts["empty_review_text"],
        "nonempty_to_classify": nonempty,
        "distinct_nonempty_texts": distinct,
        "exact_duplicate_text_rows": counts["exact_duplicate_text_rows"],
        "missing_app_version": counts["missing_app_version"],
        "reviews_by_rating": dict(sorted(ratings.items())),
        "reviews_by_month": dict(sorted(months.items())),
        "first_review": con.execute("SELECT MIN(review_timestamp) FROM reviews").fetchone()[0],
        "last_review": con.execute("SELECT MAX(review_timestamp) FROM reviews").fetchone()[0],
        "seconds": round(time.time() - started, 1),
    }

    # Compare against the published manifest when ingesting the official file.
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    official = manifest["files"]["spotify_reviews_18months.csv"]
    if report["input_sha256"] == official["sha256"]:
        expected = {"records": 660622, "duplicate_review_ids": 0, "empty_review_text_quarantined": 13,
                    "missing_app_version": 159701, "distinct_nonempty_texts": 484189}
        report["manifest_check"] = {k: {"expected": v, "actual": report[k], "ok": report[k] == v}
                                    for k, v in expected.items()}
    con.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", [
        ("input_path", str(input_path)), ("input_sha256", report["input_sha256"]), ("records", str(report["records"]))])
    con.commit()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, type=lambda p: (ROOT / p).resolve())
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--report", default=ROOT / "outputs" / "ingestion_report.json")
    args = ap.parse_args()
    report = ingest(args.input, args.db)
    write_json(args.report, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("reviews_by_month",)}, indent=2))


if __name__ == "__main__":
    main()
