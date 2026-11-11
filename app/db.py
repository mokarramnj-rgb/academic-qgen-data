"""SQLite access for Question Paper Studio."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "qbank.sqlite"
SCHEMA = ROOT / "schema.sql"
SEED = ROOT / "seed" / "class8_science_p6.json"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init(conn: sqlite3.Connection, seed: bool = True) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    if seed:
        seed_bank(conn)
    conn.commit()


def seed_bank(conn: sqlite3.Connection, path: Path = SEED, force: bool = False) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data["meta"]
    if force:
        ids = [q["id"] for q in data["questions"]]
        conn.executemany("DELETE FROM bank WHERE id = ?", [(i,) for i in ids])

    rows = []
    for q in data["questions"]:
        rows.append(
            (
                q["id"],
                str(meta.get("class_name", "")),
                meta.get("subject", ""),
                str(meta.get("chapter", "")),
                meta.get("chapter_title", ""),
                meta.get("page"),
                q["type"],
                q["stem"],
                q.get("stimulus"),
                json.dumps(q.get("options", []), ensure_ascii=False),
                q.get("answer_index"),
                q.get("answer_text"),
                json.dumps(q.get("subquestions", []), ensure_ascii=False),
                q.get("explanation"),
                int(q.get("marks", 1)),
                q.get("bloom", "remember"),
                meta.get("source", "NCTB"),
            )
        )

    conn.executemany(
        """
        INSERT OR IGNORE INTO bank
            (id, class_name, subject, chapter, chapter_title, page, type, stem,
             stimulus, options, answer_index, answer_text, subquestions,
             explanation, marks, bloom, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
