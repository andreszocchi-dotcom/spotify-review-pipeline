"""Stage 2 - Enrich. Classifies every pending distinct text with Jev (role: enrich).

Work comes from the ingested `reviews` table: one entry per distinct nonempty text (the canonical
review ID), skipping texts that already have a result under the same LABEL_CONFIG. Duplicate texts
reuse that result at export time with direct cache provenance.

Each Jev request carries exactly one review (well under the 50-review limit) and asks topic, intent,
severity and sentiment together. Work is dispatched in batches of up to 50 reviews; every finished
review is committed atomically with its call log, so an interruption loses at most in-flight calls.

Controls:
  * bounded retries with exponential backoff + jitter for rate limits / transient errors;
  * one retry for invalid output, then the review is quarantined with its reason;
  * a cumulative token cap: before each call the worst-case usage is reserved, and no new call is
    admitted when spent + reserved + next reservation would exceed the cap;
  * --stop-after-batches simulates an interruption for the resume demonstration.

    python -m pipeline.enrich --db work/state.sqlite --workers 1 --token-cap 2000000
"""

import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from typesafe_sdk import (AsyncTypeSafeClient, RetryPolicy, TypeSafeAPIConnectionError, TypeSafeAPITimeoutError,
                          TypeSafeError, TypeSafeInternalServerError, TypeSafeRateLimitError)

from pipeline import extract, labels
from pipeline.common import DEFAULT_DB, ROOT, log_call, now, open_state

BATCH_SIZE = 50
MAX_TRANSIENT_ATTEMPTS = 4
MAX_INVALID_ATTEMPTS = 2  # the original attempt plus one retry
RESERVE_INPUT, RESERVE_OUTPUT = 1500, 300  # worst-case tokens reserved per call before dispatch
NEEDS_REVIEW_CONFIDENCE = 0.5
JEV_SETTINGS = {"endpoint": "system_one", "questions": ["topic", "intent", "severity", "sentiment"],
                "reviews_per_request": 1, "sdk_retries": 0}
TRANSIENT = (TypeSafeRateLimitError, TypeSafeInternalServerError, TypeSafeAPIConnectionError, TypeSafeAPITimeoutError)



class BudgetStop(Exception):
    pass


class Ledger:
    """Shared token ledger: spent tokens plus reservations for in-flight calls."""

    def __init__(self, spent, cap):
        self.spent, self.reserved, self.cap = spent, 0, cap

    def reserve(self):
        need = RESERVE_INPUT + RESERVE_OUTPUT
        if self.cap is not None and self.spent + self.reserved + need > self.cap:
            raise BudgetStop(f"token cap {self.cap:,} reached (spent {self.spent:,}, reserved {self.reserved:,})")
        self.reserved += need
        return need

    def settle(self, reservation, used):
        self.reserved -= reservation
        self.spent += used


def validate(resp, text):
    """Map a Jev response into the common schema, or raise ValueError with the reason."""
    a = resp.answers
    topic, intent, sev, sent = a["topic"].choice, a["intent"].choice, a["severity"].choice, a["sentiment"].score
    if topic not in labels.TOPICS:
        raise ValueError(f"invalid topic {topic!r}")
    if intent not in labels.INTENTS:
        raise ValueError(f"invalid intent {intent!r}")
    if sev not in labels.SEVERITY:
        raise ValueError(f"invalid severity {sev!r}")
    if sent is None or not 0 <= sent <= 4:
        raise ValueError(f"invalid sentiment score {sent!r}")
    if resp.model != labels.JEV_MODEL:
        raise ValueError(f"model drift: requested {labels.JEV_MODEL}, served {resp.model}")
    quote = extract.evidence_quote(text, topic)
    if not quote or quote not in text:
        raise ValueError("evidence quote is not an exact source substring")
    conf = {k: {"confidence": a[k].confidence, "probabilities": {str(o): p for o, p in a[k].probabilities.items()}}
            for k in ("topic", "intent", "severity", "sentiment")}
    needs_review = min(a[k].confidence for k in ("topic", "intent", "severity")) < NEEDS_REVIEW_CONFIDENCE
    return {
        "topic": topic, "intent": intent, "severity": int(sev), "sentiment": labels.sentiment_from_score(sent),
        "entities": extract.entities(text), "evidence_quote": quote, "needs_review": needs_review, "confidence": conf,
    }


class Enricher:
    def __init__(self, con, client, ledger, run_id, phase):
        self.con, self.client, self.ledger, self.run_id, self.phase = con, client, ledger, run_id, phase
        self.questions = labels.questions()
        self.stats = {"completed": 0, "quarantined": 0, "calls": 0, "failed_calls": 0, "input_tokens": 0, "output_tokens": 0}

    def log_call(self, review_id, attempt, outcome, started, seconds, usage=None, error=None):
        log_call(self.con, run_id=self.run_id, role="enrich", provider="typesafe", review_ids=[review_id],
                 model=labels.JEV_MODEL, settings=JEV_SETTINGS, phase=self.phase, outcome=outcome,
                 label_config=labels.LABEL_CONFIG, started=started, seconds=seconds, attempt=attempt,
                 input_tokens=usage and usage.input_tokens, output_tokens=usage and usage.output_tokens, error=error)
        self.stats["calls"] += 1
        self.stats["failed_calls"] += outcome == "failed"
        if usage:
            self.stats["input_tokens"] += usage.input_tokens
            self.stats["output_tokens"] += usage.output_tokens

    async def classify(self, review_id, text_sha, text):
        invalid, attempt, last_error = 0, 0, None
        while attempt < MAX_TRANSIENT_ATTEMPTS:
            attempt += 1
            reservation = self.ledger.reserve()  # raises BudgetStop before any spend
            started, t0, usage = now(), time.perf_counter(), None
            try:
                resp = await self.client.system_one(state=text, questions=self.questions, model=labels.JEV_MODEL)
                usage = resp.usage
                record = validate(resp, text)
            except TRANSIENT as e:
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                self.log_call(review_id, attempt, "failed", started, time.perf_counter() - t0, error=last_error)
                self.ledger.settle(reservation, 0)
                await asyncio.sleep(min(30, 2 ** attempt) * (1 - 0.25 * random.random()))
                continue
            except TypeSafeError as e:  # not retryable (bad request, auth, ...)
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                self.log_call(review_id, attempt, "failed", started, time.perf_counter() - t0, error=last_error)
                self.ledger.settle(reservation, 0)
                break
            except ValueError as e:  # the call succeeded and was billed, but its output is unusable
                last_error = f"invalid_output: {e}"
                self.log_call(review_id, attempt, "failed", started, time.perf_counter() - t0, usage, last_error)
                self.ledger.settle(reservation, usage.input_tokens + usage.output_tokens)
                invalid += 1
                if invalid >= MAX_INVALID_ATTEMPTS:
                    break
                continue
            self.log_call(review_id, attempt, "succeeded", started, time.perf_counter() - t0, usage)
            self.ledger.settle(reservation, usage.input_tokens + usage.output_tokens)
            self.save_result(review_id, text_sha, record)
            return
        self.con.execute("INSERT OR REPLACE INTO quarantine VALUES (?,?,?,?)",
                         (review_id, last_error or "enrichment_failed", attempt, "enrich"))
        self.con.commit()
        self.stats["quarantined"] += 1

    def save_result(self, review_id, text_sha, r):
        self.con.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            text_sha, labels.LABEL_CONFIG, review_id, r["topic"], r["intent"], r["sentiment"], r["severity"],
            json.dumps(r["entities"]), r["evidence_quote"], int(r["needs_review"]), json.dumps(r["confidence"]),
            self.run_id, now()))
        self.con.execute("DELETE FROM quarantine WHERE review_id = ? AND stage = 'enrich'", (review_id,))
        self.con.commit()  # result and its call log land together
        self.stats["completed"] += 1


def pending(con, retry_failed, limit):
    sql = """SELECT r.review_id, r.text_sha256, r.review_text FROM reviews r
             WHERE r.is_empty = 0 AND r.review_id = r.canonical_id
               AND NOT EXISTS (SELECT 1 FROM results x WHERE x.text_sha256 = r.text_sha256 AND x.label_config = ?)"""
    if not retry_failed:
        sql += " AND NOT EXISTS (SELECT 1 FROM quarantine q WHERE q.review_id = r.review_id AND q.stage = 'enrich')"
    sql += " ORDER BY r.row_idx"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return con.execute(sql, (labels.LABEL_CONFIG,)).fetchall()


async def run(args):
    load_dotenv(ROOT / ".env")
    con = open_state(args.db)
    run_id = args.run_id or f"enrich-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    prior = con.execute("SELECT COUNT(*) FROM results WHERE label_config = ?", (labels.LABEL_CONFIG,)).fetchone()[0]
    phase = args.phase or ("resume" if prior else "initial")
    spent = con.execute("SELECT COALESCE(SUM(input_tokens),0) + COALESCE(SUM(output_tokens),0) FROM calls "
                        "WHERE role = 'enrich'").fetchone()[0]
    ledger = Ledger(spent, args.token_cap)
    con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (run_id, "enrich", now(), None,
                json.dumps({**vars(args), "db": str(args.db), "label_config": labels.LABEL_CONFIG, "phase": phase}), None))
    con.commit()

    work = pending(con, args.retry_failed, args.limit)
    print(f"[{run_id}] phase={phase} label_config={labels.LABEL_CONFIG} pending={len(work)} "
          f"already_completed={prior} tokens_spent={spent:,} cap={args.token_cap}")
    started = time.perf_counter()
    stop_reason = "done"
    async with AsyncTypeSafeClient(retry=RetryPolicy(max_retries=0, timeout=args.timeout)) as client:
        enricher = Enricher(con, client, ledger, run_id, phase)
        sem = asyncio.Semaphore(args.workers)

        async def one(row):
            async with sem:
                await enricher.classify(*row)

        try:
            for b, i in enumerate(range(0, len(work), BATCH_SIZE), 1):
                if args.stop_after_batches and b > args.stop_after_batches:
                    stop_reason = f"simulated interruption after {args.stop_after_batches} batches"
                    break
                results = await asyncio.gather(*(one(r) for r in work[i:i + BATCH_SIZE]), return_exceptions=True)
                stops = [r for r in results if isinstance(r, BudgetStop)]
                errors = [r for r in results if isinstance(r, BaseException) and not isinstance(r, BudgetStop)]
                if errors:
                    raise errors[0]
                s = enricher.stats
                print(f"  batch {b}: completed={s['completed']} quarantined={s['quarantined']} calls={s['calls']} "
                      f"failed_calls={s['failed_calls']} tokens={s['input_tokens']:,}/{s['output_tokens']:,} "
                      f"elapsed={time.perf_counter() - started:.1f}s")
                if stops:
                    stop_reason = f"budget stop: {stops[0]}"
                    break
        except (KeyboardInterrupt, asyncio.CancelledError):
            stop_reason = "interrupted"

    summary = {**enricher.stats, "pending_at_start": len(work), "stop_reason": stop_reason,
               "wall_seconds": round(time.perf_counter() - started, 2)}
    con.execute("UPDATE runs SET ended_at = ?, summary = ? WHERE run_id = ?", (now(), json.dumps(summary), run_id))
    con.commit()
    print(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--token-cap", type=int, default=None, help="cumulative Jev tokens allowed in this database")
    ap.add_argument("--limit", type=int, default=None, help="classify at most this many pending texts")
    ap.add_argument("--stop-after-batches", type=int, default=None, help="simulate an interruption")
    ap.add_argument("--retry-failed", action="store_true", help="retry texts quarantined by an earlier run")
    ap.add_argument("--phase", choices=["initial", "resume"], default=None, help="default: resume if results exist")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--run-id", default=None)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
