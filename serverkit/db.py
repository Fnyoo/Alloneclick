import sqlite3
from datetime import datetime, timezone

from .logger import data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    action TEXT NOT NULL,
    service TEXT,
    status TEXT NOT NULL,
    detail TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(data_dir() / "serverkit.db"))
    conn.execute(SCHEMA)
    return conn


def record(action: str, service: str, status: str, detail: str = "") -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO history (ts, action, service, status, detail) VALUES (?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), action, service, status, detail),
        )


def history(limit: int = 20):
    with connect() as c:
        return c.execute(
            "SELECT ts, action, service, status, detail FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
