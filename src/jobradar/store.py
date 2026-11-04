"""SQLite storage for ads and the application tracker."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    uuid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    employer TEXT,
    location TEXT,
    remote INTEGER DEFAULT 0,
    url TEXT,
    apply_url TEXT,
    due TEXT,
    published TEXT,
    expires TEXT,
    text TEXT,
    fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS applications (
    uuid TEXT PRIMARY KEY,
    title TEXT,
    employer TEXT,
    status TEXT NOT NULL,
    note TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

STATUSES = ("saved", "applied", "interview", "offer", "rejected", "ignored")
AD_COLUMNS = {"uuid", "source", "title", "employer", "location", "remote", "url", "apply_url",
              "due", "published", "expires", "text", "fetched_at"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def get_meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))
        self.db.commit()

    def has_ad(self, uuid: str) -> bool:
        return self.db.execute("SELECT 1 FROM ads WHERE uuid = ?", (uuid,)).fetchone() is not None

    def upsert_ad(self, ad: dict) -> None:
        ad = {**ad, "fetched_at": now_iso()}
        # Column names are interpolated into the SQL, so only known columns are allowed.
        unknown = set(ad) - AD_COLUMNS
        if unknown:
            raise ValueError(f"unknown ad fields: {sorted(unknown)}")
        cols = ", ".join(ad)
        marks = ", ".join(f":{k}" for k in ad)
        self.db.execute(f"INSERT OR REPLACE INTO ads ({cols}) VALUES ({marks})", ad)
        self.db.commit()

    def delete_ad(self, uuid: str) -> None:
        # NAV's terms require removing ads once they are no longer active.
        self.db.execute("DELETE FROM ads WHERE uuid = ?", (uuid,))
        self.db.commit()

    def replace_source(self, source: str, rows: list[dict]) -> tuple[int, int]:
        """Store a full snapshot of one source; jobs no longer listed are removed."""
        for row in rows:
            self.upsert_ad(row)
        keep = {r["uuid"] for r in rows}
        old = [r["uuid"] for r in self.db.execute("SELECT uuid FROM ads WHERE source = ?", (source,))]
        gone = [u for u in old if u not in keep]
        for uuid in gone:
            self.delete_ad(uuid)
        return len(rows), len(gone)

    def ads_by_source(self, source: str) -> dict[str, dict]:
        rows = self.db.execute("SELECT * FROM ads WHERE source = ?", (source,)).fetchall()
        return {r["uuid"]: {k: r[k] for k in r.keys() if k in AD_COLUMNS - {"fetched_at"}} for r in rows}

    def active_ads(self) -> list[dict]:
        rows = self.db.execute(
            """SELECT a.*, p.status FROM ads a LEFT JOIN applications p USING (uuid)
               WHERE a.expires IS NULL OR a.expires = '' OR a.expires >= ?""",
            (now_iso(),),
        ).fetchall()
        return [dict(r) for r in rows]

    def set_status(self, uuid: str, status: str, note: str | None = None) -> dict:
        ad = self.db.execute("SELECT title, employer FROM ads WHERE uuid = ?", (uuid,)).fetchone()
        old = self.db.execute("SELECT * FROM applications WHERE uuid = ?", (uuid,)).fetchone()
        if not ad and not old:
            raise KeyError(uuid)
        src = ad or old
        self.db.execute(
            "INSERT OR REPLACE INTO applications VALUES (?, ?, ?, ?, ?, ?)",
            (uuid, src["title"], src["employer"], status, note or (old["note"] if old else None), now_iso()),
        )
        self.db.commit()
        return {"title": src["title"], "employer": src["employer"]}

    def applications(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def resolve(self, prefix: str) -> str:
        """Allow short uuid prefixes on the command line."""
        rows = self.db.execute(
            "SELECT uuid FROM ads WHERE uuid LIKE ? UNION SELECT uuid FROM applications WHERE uuid LIKE ?",
            (prefix + "%", prefix + "%"),
        ).fetchall()
        if len(rows) != 1:
            raise KeyError(f"{prefix!r} matches {len(rows)} ads")
        return rows[0]["uuid"]
