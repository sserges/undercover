"""The UnderCover database in SQLite, and the fixed documents from data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY, status TEXT NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (
    claim_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    payout REAL NOT NULL,
    reasons TEXT NOT NULL,
    policy_section TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    claim_id TEXT PRIMARY KEY, amount REAL NOT NULL, paid_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sign_offs (
    claim_id TEXT PRIMARY KEY, handler_id TEXT NOT NULL, signed_off_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

DROP = """
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS handlers;
DROP TABLE IF EXISTS decisions;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS sign_offs;
DROP TABLE IF EXISTS steps;
"""


def read_json(name: str) -> Any:
    """Read a JSON file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


COMPANY = read_json("company.json")
PLANS = {plan["plan"]: plan for plan in read_json("plans.json")["plans"]}
POLICY_WORDING = (DATA / "policy_wording.md").read_text(encoding="utf-8")


def path() -> Path:
    """Return the database file: UNDERCOVER_DB, or backend/undercover.db."""
    return Path(os.getenv("UNDERCOVER_DB", ROOT / "backend" / "undercover.db"))


def dict_row(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        column[0]: value for column, value in zip(cursor.description, row, strict=True)
    }


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database with rows as dicts, commit the block's changes, then close."""
    conn = sqlite3.connect(path())
    conn.row_factory = dict_row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def seed(conn: sqlite3.Connection) -> None:
    """Load the claims queue, policies, customers and handlers from data/."""
    claims = read_json("claims.json")
    conn.executemany(
        "INSERT INTO claims VALUES (?, 'waiting', ?)",
        [
            (
                claim["claim_id"],
                json.dumps({k: v for k, v in claim.items() if k != "status"}),
            )
            for claim in claims
        ],
    )
    for insert, file, key in [
        ("INSERT INTO policies VALUES (?, ?)", "policies.json", "policy_id"),
        ("INSERT INTO customers VALUES (?, ?)", "customers.json", "customer_id"),
        ("INSERT INTO handlers VALUES (?, ?)", "handlers.json", "handler_id"),
    ]:
        conn.executemany(
            insert, [(row[key], json.dumps(row)) for row in read_json(file)]
        )


def init() -> None:
    """Create the tables, and seed them if the queue is empty."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()["n"] == 0:
            seed(conn)


def reset() -> None:
    """Drop every table and seed the database again from data/."""
    with connect() as conn:
        conn.executescript(DROP)
    init()


if __name__ == "__main__":
    reset()
    print(f"Seeded {path()} from data/")
