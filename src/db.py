"""SQLite ingest + query helpers."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def ingest_jsonl(conn: sqlite3.Connection, path: Path) -> int:
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            conn.execute(
                """INSERT OR REPLACE INTO questions
                   (id, source, url, class_name, subject, chapter, stem, options,
                    answer_index, answer_text, tags, answer_status, fingerprint)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    q["id"], q["source"], q.get("url"), q.get("class_name"),
                    q.get("subject"), q.get("chapter"), q["stem"],
                    json.dumps(q["options"], ensure_ascii=False),
                    q.get("answer_index"), q.get("answer_text"),
                    json.dumps(q.get("tags", []), ensure_ascii=False),
                    q.get("answer_status", "missing"), q["fingerprint"],
                ),
            )
            n += 1
    conn.commit()
    return n


def stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        """SELECT class_name, COUNT(*) AS n,
                  SUM(answer_index IS NOT NULL) AS with_answer
           FROM questions GROUP BY class_name ORDER BY class_name"""
    ).fetchall()
    return {r["class_name"] or "unknown": {"n": r["n"], "with_answer": r["with_answer"]}
            for r in rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load parsed questions into SQLite.")
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--db", type=Path, required=True)
    args = ap.parse_args(argv)

    conn = connect(args.db)
    n = ingest_jsonl(conn, args.jsonl)
    print(f"loaded {n} rows -> {args.db}")
    for cls, s in stats(conn).items():
        print(f"  class {cls}: {s['n']} questions ({s['with_answer']} with answer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
