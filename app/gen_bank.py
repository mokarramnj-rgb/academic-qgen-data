#!/usr/bin/env python3
"""Build the Class 8 Science question bank from a curated NCTB fact base.

Source of facts: NCTB অষ্টম শ্রেণি বিজ্ঞান পাঠ্যবই (OCR in data/nctb8_ocr).
Only one question is generated per atomic fact, and a global near-duplicate
guard drops overlapping stems, so the bank stays clean.

    python3 app/gen_bank.py            # write seed/class8_science_all.json
    python3 app/gen_bank.py --report   # print per-chapter counts only
"""
from __future__ import annotations

import argparse
import json
import re
import random
from collections import defaultdict
from pathlib import Path

from facts import CHAPTERS

# Optional second pass: extra facts/groups appended per chapter.
try:  # pragma: no cover - convenience import
    from facts_extra import EXTRA
except ImportError:  # noqa: BLE001
    EXTRA = {}
for _ch, _ex in EXTRA.items():
    _base = CHAPTERS.setdefault(_ch, {})
    for _k in ("defs", "mcq", "groups", "nums", "kh", "cq"):
        if _ex.get(_k):
            _base[_k] = list(_base.get(_k, [])) + list(_ex[_k])

# Optional third pass.
try:  # pragma: no cover
    from facts_extra2 import EXTRA2
except ImportError:  # noqa: BLE001
    EXTRA2 = {}
for _ch, _ex in EXTRA2.items():
    _base = CHAPTERS.setdefault(_ch, {})
    for _k in ("defs", "mcq", "groups", "nums", "kh", "cq"):
        if _ex.get(_k):
            _base[_k] = list(_base.get(_k, [])) + list(_ex[_k])

ROOT = Path(__file__).resolve().parent
SEED = ROOT / "seed" / "class8_science_all.json"
BN = "০১২৩৪৫৬৭৮৯"
_bn_tbl = str.maketrans("0123456789", BN)


def bn(n) -> str:
    return str(n).translate(_bn_tbl)


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\u0980-\u09FF]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def grams(s: str, n: int = 5) -> set:
    w = norm(s).split()
    if len(w) < n:
        return {tuple(w)} if w else set()
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def ensure_danda(s: str) -> str:
    s = (s or "").strip()
    if s and not re.search(r"[।?!]$", s):
        s += "।"
    return s


class Deduper:
    """Global guard against exact and near-duplicate questions."""

    THRESHOLD = 0.72

    def __init__(self):
        self.exact: set[str] = set()
        self.by_type: dict[str, list[tuple[str, set]]] = defaultdict(list)
        self.option_sets: set[tuple] = set()
        self.dropped = defaultdict(int)

    def accept(self, q: dict) -> bool:
        basis = (q.get("stimulus") or "") + " " + q["stem"] if q["type"] == "cq" else q["stem"]
        key = norm(basis)
        if not key:
            self.dropped["empty"] += 1
            return False
        if key in self.exact:
            self.dropped["exact"] += 1
            return False
        g = grams(basis)
        for _, other in self.by_type[q["type"]]:
            if jaccard(g, other) >= self.THRESHOLD:
                self.dropped["near"] += 1
                return False
        if q["type"] == "mcq":
            osig = tuple(sorted(norm(o) for o in q.get("options") or []))
            if len(set(osig)) < 4:
                self.dropped["bad_options"] += 1
                return False
        self.exact.add(key)
        self.by_type[q["type"]].append((key, g))
        return True


def shuffled_options(answer: str, distractors: list[str], seed: int) -> tuple[list[str], int]:
    # Preserve maths symbols (=, ×, ÷, +) so formula options stay distinct.
    def key(s):
        return re.sub(r"\s+", " ", str(s).strip().lower())
    opts = [answer] + [d for d in distractors if key(d) != key(answer)]
    assert len(opts) >= 4, (answer, distractors)
    opts = opts[:4]
    rnd = random.Random(seed)
    rnd.shuffle(opts)
    return opts, next(i for i, o in enumerate(opts) if key(o) == key(answer)) + 1


def make(ch, title, typ, stem, seq, *, options=None, answer_index=None,
         answer_text="", marks=1, bloom="remember", difficulty=1,
         stimulus="", subquestions=None, explanation=""):
    return {
        "id": f"c8s-c{ch}-{typ}-{seq:02d}",
        "type": typ,
        "stem": stem.strip(),
        "options": options or [],
        "answer_index": answer_index,
        "answer_text": answer_text.strip(),
        "marks": marks,
        "bloom": bloom,
        "explanation": explanation,
        "difficulty": difficulty,
        "class_name": "8",
        "subject": "বিজ্ঞান",
        "chapter_title": title,
        "source": "NCTB অষ্টম শ্রেণি বিজ্ঞান (পাঠ্যবই ভিত্তিক)",
        "chapter": str(ch),
    } if typ != "cq" else {
        "id": f"c8s-c{ch}-{typ}-{seq:02d}",
        "type": typ,
        "stem": stem.strip(),
        "stimulus": stimulus.strip(),
        "subquestions": subquestions or [],
        "answer_text": answer_text.strip(),
        "marks": sum(s["marks"] for s in (subquestions or [])),
        "bloom": bloom,
        "explanation": explanation,
        "difficulty": difficulty,
        "class_name": "8",
        "subject": "বিজ্ঞান",
        "chapter_title": title,
        "source": "NCTB অষ্টম শ্রেণি বিজ্ঞান (পাঠ্যবই ভিত্তিক)",
        "chapter": str(ch),
    }


def build_chapter(ch: int, data: dict, dedupe: Deduper) -> list[dict]:
    title = data["title"]
    out: list[dict] = []
    counters = defaultdict(int)

    def add(q):
        if dedupe.accept(q):
            counters[q["type"]] += 1
            q["id"] = f"c8s-c{ch}-{q['type']}-{counters[q['type']]:02d}"
            out.append(q)

    # 1. Definitions -> জ্ঞানমূলক short questions
    for item in data.get("defs", []):
        term, definition = item[0], item[1]
        stem = item[2] if len(item) > 2 else f"{term} কী?"
        add(make(ch, title, "wrq_k", stem, 0,
                 answer_text=ensure_danda(definition), marks=1,
                 bloom="remember", difficulty=1,
                 explanation=ensure_danda(definition)))

    # 2. Direct MCQs (highest-confidence curated items)
    for i, item in enumerate(data.get("mcq", [])):
        q, a, dists = item[0], item[1], list(item[2])
        opts, idx = shuffled_options(a, dists, ch * 1000 + i)
        add(make(ch, title, "mcq", q, 0, options=opts, answer_index=idx,
                 answer_text=a, marks=1,
                 bloom=("remember" if i % 3 == 0 else "understand"),
                 difficulty=(1 if i % 3 == 0 else 2 if i % 3 == 1 else 3),
                 explanation=item[3] if len(item) > 3 else ""))

    # 3. Classification groups -> member->group and group->member MCQs
    groups = data.get("groups", [])
    by_cat = defaultdict(list)
    for g in groups:
        by_cat[g["cat"]].append(g)
    n = 0
    for g in groups:
        siblings = by_cat[g["cat"]]
        other_names = [x["name"] for x in siblings if x["name"] != g["name"]]
        other_members = [m for x in siblings if x["name"] != g["name"] for m in x["members"]]
        # member -> group
        for mi, m in enumerate(g["members"]):
            if len(other_names) < 3:
                break
            q = g["member_q"].format(m=m, g=g["name"])
            pool = list(other_names)
            random.Random(ch * 7000 + n).shuffle(pool)
            opts, idx = shuffled_options(g["name"], pool[:3], ch * 7000 + n)
            n += 1
            add(make(ch, title, "mcq", q, 0, options=opts, answer_index=idx,
                     answer_text=g["name"], marks=1, bloom="understand",
                     difficulty=1, explanation=f"{m} {g['name']} {g.get('label', '')}-এর অন্তর্ভুক্ত।"))
        # group -> member
        if len(other_members) >= 3:
            q = g["group_q"].format(g=g["name"])
            dists = random.Random(ch * 31 + n).sample(other_members, 3)
            answer = g["members"][0]
            opts, idx = shuffled_options(answer, dists, ch * 9000 + n)
            n += 1
            add(make(ch, title, "mcq", q, 0, options=opts, answer_index=idx,
                     answer_text=answer, marks=1, bloom="understand",
                     difficulty=2, explanation=f"{answer} একটি {g['name']}।"))

    # 4. Extra numeric / data MCQs
    for i, item in enumerate(data.get("nums", [])):
        q, a, dists = item[0], item[1], list(item[2])
        opts, idx = shuffled_options(a, dists, ch * 13000 + i)
        add(make(ch, title, "mcq", q, 0, options=opts, answer_index=idx,
                 answer_text=a, marks=1, bloom="understand", difficulty=2,
                 explanation=item[3] if len(item) > 3 else ""))

    # 4b. New curated MCQs from per-chapter JSON files (one question per fact).
    for i, item in enumerate(data.get("extra_mcq", [])):
        q, a, dists = item[0], item[1], list(item[2])
        opts, idx = shuffled_options(a, dists, ch * 50000 + i)
        add(make(ch, title, "mcq", q, 0, options=opts, answer_index=idx,
                 answer_text=a, marks=1, bloom="remember",
                 difficulty=(1 if i % 2 == 0 else 2),
                 explanation=""))

    # 4c. New short-answer questions -> জ্ঞানমূলক
    for i, item in enumerate(data.get("extra_short", [])):
        q, a = item[0], item[1]
        add(make(ch, title, "wrq_k", q, 0,
                 answer_text=ensure_danda(a), marks=1,
                 bloom="remember", difficulty=1,
                 explanation=ensure_danda(a)))

    # 4d. New explanation questions -> অনুধাবনমূলক
    for i, item in enumerate(data.get("extra_kh", [])):
        q, a = item[0], item[1]
        add(make(ch, title, "wrq_kh", q, 0,
                 answer_text=ensure_danda(a), marks=2,
                 bloom="understand", difficulty=2,
                 explanation=ensure_danda(a)))

    # 5. Explanation questions -> অনুধাবনমূলক
    for i, (q, a) in enumerate(data.get("kh", [])):
        add(make(ch, title, "wrq_kh", q, 0, answer_text=ensure_danda(a),
                 marks=2, bloom="understand",
                 difficulty=(2 if i % 3 else 3),
                 explanation=ensure_danda(a)))

    # 6. Creative questions -> সৃজনশীল
    for i, cq in enumerate(data.get("cq", [])):
        stimulus, subs, answer = cq[0], cq[1], cq[2]
        subquestions = [
            {"label": lab, "text": txt, "marks": mk}
            for lab, (txt, mk) in zip("কখগঘ", subs)
        ]
        add(make(ch, title, "cq", (stimulus[:50] + "…"), 0,
                 stimulus=stimulus, subquestions=subquestions,
                 answer_text=answer, marks=10, bloom="apply",
                 difficulty=2, explanation=""))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    dedupe = Deduper()
    questions: list[dict] = []
    report = {}
    for ch in sorted(CHAPTERS):
        data = CHAPTERS[ch]
        # Merge per-chapter curated JSON additions (one question per fact).
        p = ROOT / "gen" / f"extra_ch{ch}.json"
        if p.exists():
            ed = json.loads(p.read_text(encoding="utf-8"))
            for k, key in (("mcq", "extra_mcq"), ("short", "extra_short"), ("kh", "extra_kh")):
                if ed.get(k):
                    data.setdefault(key, []).extend(ed[k])
        qs = build_chapter(ch, data, dedupe)
        questions.extend(qs)
        by = defaultdict(int)
        for q in qs:
            by[q["type"]] += 1
        report[ch] = (len(qs), dict(by), len(data.get("defs", [])),
                      len(data.get("mcq", [])), len(data.get("groups", [])))

    print(f"total questions: {len(questions)}")
    for ch, (total, by, nd, nm, ng) in report.items():
        print(f"  ch{ch:2d} {CHAPTERS[ch]['title'][:28]:30s} total={total:4d} "
              f"mcq={by.get('mcq', 0):3d} k={by.get('wrq_k', 0):3d} "
              f"kh={by.get('wrq_kh', 0):3d} cq={by.get('cq', 0):2d} "
              f"(defs={nd} mcq={nm} groups={ng})")
    print("dropped:", dict(dedupe.dropped))

    if args.report:
        return 0

    meta = {
        "class_name": "8",
        "subject": "বিজ্ঞান",
        "source": "NCTB অষ্টম শ্রেণি বিজ্ঞান (পাঠ্যবই ভিত্তিক)",
        "note": ("NCTB পাঠ্যবই ভিত্তিক; প্রতিটি প্রশ্ন একটি স্বতন্ত্র তথ্যের উপর "
                 "তৈরি এবং ডুপ্লিকেট-মুক্ত যাচাই করা।"),
        "chapters": len(CHAPTERS),
        "chapter_map": {str(ch): CHAPTERS[ch]["title"] for ch in sorted(CHAPTERS)},
        "bank_version": 2,
        "generated_by": "app/gen_bank.py",
    }
    payload = {"meta": meta, "questions": questions}
    SEED.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {SEED} ({SEED.stat().st_size/1024/1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
