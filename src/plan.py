"""Curriculum graph + SM-2 spaced repetition planner."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from .db import connect


@dataclass
class Node:
    id: str
    class_name: str
    subject: str
    chapter: str
    title: str = ""
    ord: int = 0
    prereqs: tuple[str, ...] = ()


def sm2(ease: float, interval: int, reps: int, quality: int) -> tuple[float, int, int]:
    """quality: 0..5. Returns (ease, interval_days, reps)."""
    if quality < 3:
        return ease, 1, 0
    ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if reps == 0:
        interval = 1
    elif reps == 1:
        interval = 6
    else:
        interval = round(interval * ease)
    return ease, interval, reps + 1


def topo(nodes: list[Node]) -> list[Node]:
    by_id = {n.id: n for n in nodes}
    done: set[str] = set()
    order: list[Node] = []

    def visit(n: Node, stack: set[str]) -> None:
        if n.id in done or n.id in stack:
            return
        stack.add(n.id)
        for p in n.prereqs:
            if p in by_id:
                visit(by_id[p], stack)
        stack.discard(n.id)
        done.add(n.id)
        order.append(n)

    for n in sorted(nodes, key=lambda x: (x.class_name, x.subject, x.ord)):
        visit(n, set())
    return order


def load_nodes(conn: sqlite3.Connection, curriculum: Path | None) -> list[Node]:
    if curriculum:
        raw = json.loads(curriculum.read_text(encoding="utf-8"))
        return [Node(**r) for r in raw]

    # Fallback: derive pseudo-nodes from ingested questions.
    rows = conn.execute(
        """SELECT class_name, COALESCE(subject,'general') AS subject, COUNT(*) n
           FROM questions GROUP BY class_name, subject ORDER BY class_name, subject"""
    ).fetchall()
    nodes, prev_by_subject = [], {}
    for r in rows:
        cls, subj = r["class_name"] or "unknown", r["subject"]
        nid = f"{cls}/{subj}/all"
        prereqs = (prev_by_subject[subj],) if subj in prev_by_subject else ()
        nodes.append(Node(nid, cls, subj, "all", 0, prereqs))
        prev_by_subject[subj] = nid
    return nodes


def mastery_map(conn: sqlite3.Connection, user: str) -> dict[str, float]:
    rows = conn.execute(
        "SELECT node_id, mastery FROM schedule WHERE user_id=?", (user,)
    ).fetchall()
    return {r["node_id"]: r["mastery"] for r in rows}


def build_plan(nodes: list[Node], mastery: dict[str, float],
               weeks: int) -> list[dict]:
    ordered = topo(nodes)
    ids = {n.id for n in nodes}
    by_id = {n.id: n for n in nodes}

    # Weakest first, but only after prerequisites are at least 60% mastered.
    def ready(n: Node) -> bool:
        return all(mastery.get(p, 0.0) >= 0.6 for p in n.prereqs if p in ids)

    def depth(node_id: str, stack: frozenset[str] = frozenset()) -> int:
        """Dependency depth, so prerequisites are always scheduled first."""
        n = by_id[node_id]
        if node_id in stack:
            return 0
        parents = [p for p in n.prereqs if p in by_id]
        return 1 + max((depth(p, stack | {node_id}) for p in parents), default=-1)

    pending = [n for n in ordered if mastery.get(n.id, 0.0) < 0.8]
    pending.sort(key=lambda n: (depth(n.id), mastery.get(n.id, 0.0), n.ord))

    per_week = max(1, (len(pending) + weeks - 1) // weeks)
    plan, day = [], dt.date.today()
    for w in range(weeks):
        chunk = pending[w * per_week:(w + 1) * per_week]
        entry = {"week": w + 1, "start": day.isoformat(), "focus": [], "daily": []}
        for n in chunk:
            entry["focus"].append({
                "node": n.id,
                "mastery": round(mastery.get(n.id, 0.0), 2),
                "prereqs_done": ready(n),
            })
        for d in range(7):
            topic = chunk[d % len(chunk)] if chunk else None
            entry["daily"].append({
                "date": (day + dt.timedelta(days=d)).isoformat(),
                "learn": topic.id if topic else "review",
                "practice": "20 MCQs + error log" if d < 5 else "spaced review",
            })
        plan.append(entry)
        day += dt.timedelta(days=7)
    return plan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build a step-by-step study plan.")
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--user", default="demo")
    ap.add_argument("--weeks", type=int, default=4)
    ap.add_argument("--curriculum", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    conn = connect(args.db)
    nodes = load_nodes(conn, args.curriculum)
    plan = build_plan(nodes, mastery_map(conn, args.user), args.weeks)

    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"plan -> {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
