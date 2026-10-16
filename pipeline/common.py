"""Shared helpers. Row parsing and hashing come from the course checker so they match grading exactly."""

import hashlib
import importlib.util
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WORK = ROOT / "work"
DEFAULT_DB = WORK / "state.sqlite"

_spec = importlib.util.spec_from_file_location("check_submission", DATA / "check_submission.py")
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

FIELDS = checker.FIELDS
TOPICS = checker.TOPICS
INTENTS = checker.INTENTS
csv_rows = checker.csv_rows
row_sha = checker.row_sha
file_sha = checker.sha


# Tables shared by every stage. Each stage adds its own outputs; all model calls go to `calls`.
STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    text_sha256 TEXT NOT NULL,
    label_config TEXT NOT NULL,
    source_review_id TEXT NOT NULL,      -- the review whose call produced this result
    topic TEXT NOT NULL, intent TEXT NOT NULL, sentiment REAL NOT NULL, severity INTEGER NOT NULL,
    entities TEXT NOT NULL, evidence_quote TEXT NOT NULL, needs_review INTEGER NOT NULL,
    confidence TEXT NOT NULL,            -- per-question confidences and probabilities from Jev
    run_id TEXT NOT NULL, completed_at TEXT NOT NULL,
    PRIMARY KEY (text_sha256, label_config)
);
CREATE TABLE IF NOT EXISTS calls (
    request_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, role TEXT NOT NULL, provider TEXT NOT NULL,
    review_ids TEXT NOT NULL, model TEXT NOT NULL, settings TEXT NOT NULL, phase TEXT NOT NULL,
    outcome TEXT NOT NULL, label_config TEXT NOT NULL,
    input_tokens INTEGER, output_tokens INTEGER, cache_read_input_tokens INTEGER, cache_creation_input_tokens INTEGER,
    attempt INTEGER NOT NULL, error TEXT, started_at TEXT NOT NULL, seconds REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS quarantine (
    review_id TEXT PRIMARY KEY, reason TEXT NOT NULL, attempts INTEGER NOT NULL, stage TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, stage TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT,
    args TEXT NOT NULL, summary TEXT);
CREATE TABLE IF NOT EXISTS artifacts (   -- downstream outputs cached by their exact inputs + config
    stage TEXT NOT NULL, input_sha256 TEXT NOT NULL, config TEXT NOT NULL, output TEXT NOT NULL,
    run_id TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY (stage, input_sha256, config)
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def open_state(db_path=DEFAULT_DB):
    con = connect(db_path)
    con.executescript(STATE_SCHEMA)
    return con


def log_call(con, *, run_id, role, provider, review_ids, model, settings, phase, outcome, label_config,
             started, seconds, attempt, input_tokens=None, output_tokens=None, cache_read=None, cache_write=None,
             error=None, request_id=None):
    con.execute("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        request_id or f"local-{uuid.uuid4()}", run_id, role, provider, json.dumps(review_ids), model,
        json.dumps(settings, sort_keys=True), phase, outcome, label_config, input_tokens, output_tokens,
        cache_read, cache_write, attempt, error, started, round(seconds, 3)))


def sha_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def connect(db_path=DEFAULT_DB):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def write_json(path, value):
    """Atomic write: a crash never leaves a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
