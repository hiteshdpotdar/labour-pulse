"""The database: one SQLite file holding stories, bills (with their stages) and each source's health."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id        TEXT PRIMARY KEY,        -- hash of the normalised URL
    url       TEXT NOT NULL,
    title     TEXT NOT NULL,
    summary   TEXT NOT NULL DEFAULT '',
    source    TEXT NOT NULL,
    lang      TEXT NOT NULL DEFAULT 'en',
    streams   TEXT NOT NULL,           -- comma-separated, main stream first
    tags      TEXT NOT NULL DEFAULT '',
    places    TEXT NOT NULL DEFAULT '',-- country codes, plus "US-CA" / "IN-MH" for states
    authors   TEXT NOT NULL DEFAULT '',
    date      TEXT NOT NULL,           -- YYYY-MM-DD, the publication day (UTC)
    added_at  TEXT NOT NULL,
    bill      TEXT,                    -- bills.key, for law-tracker cards from an official record
    lead      TEXT                     -- id of the card this story is grouped under (same event elsewhere)
);
CREATE INDEX IF NOT EXISTS items_date ON items(date);
CREATE TABLE IF NOT EXISTS bills (
    key          TEXT PRIMARY KEY,     -- "GB-3737", "IN-LS-2025-123", "MANUAL-rajasthan-gig-act"
    jurisdiction TEXT NOT NULL,        -- "GB", "IN", "IN-RJ", ...
    title        TEXT NOT NULL,
    url          TEXT NOT NULL,
    source       TEXT NOT NULL,
    summary      TEXT NOT NULL DEFAULT '',
    history      TEXT NOT NULL,        -- JSON [{date, stage, text}]
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    name        TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    last_ok     TEXT,
    failures    INTEGER NOT NULL DEFAULT 0,  -- failed fetches in a row
    last_error  TEXT NOT NULL DEFAULT '',
    last_count  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (at TEXT NOT NULL, added INTEGER NOT NULL, errors TEXT NOT NULL DEFAULT '');
"""

FAILING_AFTER = 3
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid", "gclid"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if k not in TRACKING])
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", query, ""))


def item_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode()).hexdigest()[:16]


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    # Repair: stories stored with a date that isn't YYYY-MM-DD (early Indian bill records, "30/12/1964").
    # Law-tracker cards are re-read from the official record on the next run.
    conn.execute("DELETE FROM items WHERE date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'")
    conn.commit()
    return conn


def exists(conn, url: str) -> bool:
    return conn.execute("SELECT 1 FROM items WHERE id = ?", (item_id(url),)).fetchone() is not None


def title_seen(conn, title: str, days: int = 14) -> bool:
    """The same headline already stored recently (a feed re-publishing a story under a new link)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    return conn.execute("SELECT 1 FROM items WHERE lower(title) = lower(?) AND date >= ?", (title, since)).fetchone() is not None


def insert(conn, item: dict) -> bool:
    """Store a new story. Returns False if its link is already stored."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO items (id, url, title, summary, source, lang, streams, tags, places, authors, date,"
        " added_at, bill) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (item_id(item["url"]), item["url"], item["title"], item.get("summary", ""), item["source"],
         item.get("lang", "en"), ",".join(item["streams"]), ",".join(item.get("tags", [])),
         ",".join(item.get("places", [])), ", ".join(item.get("authors", []))[:300], item["date"], now(),
         item.get("bill")))
    return cur.rowcount == 1


def update(conn, url: str, **fields) -> None:
    cols = {k: (",".join(v) if isinstance(v, list) else v) for k, v in fields.items()}
    conn.execute(f"UPDATE items SET {', '.join(f'{k} = ?' for k in cols)} WHERE id = ?", (*cols.values(), item_id(url)))


def record_source(conn, name: str, url: str, ok: bool, error: str = "", count: int = 0) -> None:
    conn.execute("INSERT OR IGNORE INTO sources (name, url) VALUES (?, ?)", (name, url))
    if ok:
        conn.execute("UPDATE sources SET url = ?, last_ok = ?, failures = 0, last_error = '', last_count = ? WHERE name = ?",
                     (url, now(), count, name))
    else:
        conn.execute("UPDATE sources SET url = ?, failures = failures + 1, last_error = ? WHERE name = ?",
                     (url, error[:300], name))


def source_health(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM sources ORDER BY failures DESC, name")]


def log_run(conn, added: int, errors: list[str]) -> None:
    conn.execute("INSERT INTO runs (at, added, errors) VALUES (?, ?, ?)", (now(), added, json.dumps(errors[:50])))


def last_run(conn) -> dict | None:
    row = conn.execute("SELECT * FROM runs ORDER BY at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def is_empty(conn) -> bool:
    return conn.execute("SELECT 1 FROM items LIMIT 1").fetchone() is None


def recent(conn, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    rows = conn.execute("SELECT * FROM items WHERE date >= ? ORDER BY date DESC, added_at DESC", (since,))
    return [dict(r) for r in rows]


def bills(conn) -> dict[str, dict]:
    out = {}
    for r in conn.execute("SELECT * FROM bills"):
        b = dict(r)
        b["history"] = json.loads(b["history"])
        out[b["key"]] = b
    return out


def prune(conn, keep_days: int) -> int:
    since = (datetime.now(timezone.utc) - timedelta(days=keep_days)).date().isoformat()
    return conn.execute("DELETE FROM items WHERE date < ? AND bill IS NULL", (since,)).rowcount
