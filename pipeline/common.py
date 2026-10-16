"""Shared helpers. Row parsing and hashing come from the course checker so they match grading exactly."""

import hashlib
import importlib.util
import json
import os
import sqlite3
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
