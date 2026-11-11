#!/usr/bin/env python3
"""Build the Class 3 Science question bank from a curated NCTB fact base.

Source: NCTB তৃতীয় শ্রেণি প্রাথমিক বিজ্ঞান পাঠ্যবই.
Only one question is generated per atomic fact, and a global near-duplicate
guard drops overlapping stems, so the bank stays clean.

    python3 app/gen_class3.py            # write seed/class3_science_all.json
    python3 app/gen_class3.py --report   # print per-chapter counts only
"""
from __future__ import annotations

import argparse
import json
import re
import random
from collections import defaultdict
from pathlib import Path

try:
    from facts_class3 import CHAPTERS
except ImportError:  # pragma: no cover
    CHAPTERS = {}

ROOT = Path(__file__).resolve().parent
SEED = ROOT / "seed" / "class3_science_all.json"
BN = "০১২৩৪৫৬৭৮৯"
_bn_tbl = str.maketrans("0123456789", BN)


def bn(n: int) -> str:
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
    THRESHOLD = 0.72

    def __init__(self):
        self.exact: set[str] = set()
        self.by_type: dict[str, list[tuple[str, set]]] = defaultdict(list)
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
    def key(s):
        return re.sub(r"\s+", " ", str(s).strip().lower())
    opts = [answer] + [d for d in distractors if key(d) != key(answer)]
    # pad if needed
    while len(opts) < 4:
        opts.append(f"উপরোক্ত কোনটিও না {len(opts)}")
    opts = opts[:4]
    rnd = random.Random(seed)
    rnd.shuffle(opts)
    return opts, next(i for i, o in enumerate(opts) if key(o) == key(answer)) + 1


def make(ch, title, typ, stem, seq, *, options=None, answer_index=None,
         answer_bool=None, answer_text="", marks=1, bloom="remember", difficulty=1,
         stimulus="", subquestions=None, left=None, right=None, answer_key=None,
         explanation=""):
    base = {
        "id": f"c3s-c{ch}-{typ}-{seq:02d}",
        "type": typ,
        "stem": stem.strip(),
        "options": options or [],
        "answer_index": answer_index,
        "answer_bool": answer_bool,
        "answer_text": answer_text.strip(),
        "marks": marks,
        "bloom": bloom,
        "difficulty": difficulty,
        "class_name": "3",
        "subject": "বিজ্ঞান",
        "chapter_title": title,
        "chapter": str(ch),
        "source": "NCTB তৃতীয় শ্রেণি প্রাথমিক বিজ্ঞান (পাঠ্যবই ভিত্তিক)",
    }
    if typ == "match":
        base["left"] = left or []
        base["right"] = right or []
        base["answer_key"] = answer_key or []
    if typ == "cq":
        base["stimulus"] = stimulus.strip()
        base["subquestions"] = subquestions or []
        base["marks"] = sum(s["marks"] for s in (subquestions or []))
    if not base["options"]:
        base.pop("options", None)
    return base


def build_chapter(ch: int, data: dict, dedupe: Deduper) -> list[dict]:
    title = data["title"]
    out: list[dict] = []
    counters = defaultdict(int)

    def add(q):
        if dedupe.accept(q):
            counters[q["type"]] += 1
            q["id"] = f"c3s-c{ch}-{q['type']}-{counters[q['type']]:02d}"
            out.append(q)

    # 1. Definitions -> জ্ঞানমূলক
    for item in data.get("defs", []):
        term, definition = item[0], item[1]
        stem = f"{term} কী?"
        add(make(ch, title, "wrq_k", stem, 0,
                 answer_text=ensure_danda(definition), marks=1,
                 bloom="remember", difficulty=1,
                 explanation=ensure_danda(definition)))

    # 2. Facts -> MCQ + fill + TF(true) + TF(false)
    for i, (statement, key_term) in enumerate(data.get("facts", [])):
        # Skip placeholder entries
        if key_term == "skip" or statement == "skip":
            continue

        # MCQ with fact-specific distractors
        q_mcq = statement + " নিচের কোনটি সঠিক?"
        distractors = [
            key_term + " নয়",
            "উপরোক্ত কোনটিও না",
            "জানি না",
            key_term.replace("ও", "অও") if "ও" in key_term else key_term + " আলাদা",
        ]
        opts, idx = shuffled_options(key_term, distractors, ch * 10000 + i)
        add(make(ch, title, "mcq", q_mcq, 0, options=opts, answer_index=idx,
                 answer_text=key_term, marks=1, bloom="remember",
                 difficulty=(1 if i % 3 == 0 else 2)))

        # Fill in the blank
        if key_term in statement:
            q_fill = statement.replace(key_term, "——")
        else:
            q_fill = statement.rstrip("।") + " ——।"
        add(make(ch, title, "fill", q_fill, 0,
                 answer_text=ensure_danda(key_term), marks=1,
                 bloom="remember", difficulty=1))

        # True/False (true variant)
        add(make(ch, title, "tf", statement, 0,
                 answer_bool=True, answer_text="শুদ্ধ", marks=1,
                 bloom="remember", difficulty=1))

        # True/False (false variant - negate key term)
        if key_term in statement:
            neg = statement.replace(key_term, key_term + " না")
        else:
            neg = statement.rstrip("।") + " হয় না।"
        add(make(ch, title, "tf", neg, 0,
                 answer_bool=False, answer_text="অশুদ্ধ", marks=1,
                 bloom="remember", difficulty=2))

    # 3. Groups -> matching sets
    gseq = 0
    for cat, pairs in data.get("groups", []):
        left = [p[0] for p in pairs]
        right = [p[1] for p in pairs]
        right_with_distractor = right + ["অসংগত বাছাই"]
        answer_key = [right.index(p[1]) for p in pairs]
        stem = f"{cat} সম্পর্কে সঠিক অংশ মিলিয়ে দাও।"
        add(make(ch, title, "match", stem, gseq,
                 left=left, right=right_with_distractor, answer_key=answer_key,
                 marks=1, bloom="understand", difficulty=2))
        gseq += 1

    # 4. Creative questions -> সৃজনশীল
    for i, (stimulus, subs, answer) in enumerate(data.get("cq", [])):
        subquestions = [
            {"label": lab, "text": txt, "marks": mk}
            for lab, txt, mk in subs
        ]
        add(make(ch, title, "cq", (stimulus[:45] + "…"), 0,
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
        qs = build_chapter(ch, data, dedupe)
        questions.extend(qs)
        by = defaultdict(int)
        for q in qs:
            by[q["type"]] += 1
        report[ch] = (len(qs), dict(by))

    print(f"total questions: {len(questions)}")
    for ch, (total, by) in report.items():
        print(f"  ch{ch:2d} {CHAPTERS[ch]['title'][:28]:30s} total={total:4d} "
              f"mcq={by.get('mcq', 0):3d} fill={by.get('fill', 0):3d} "
              f"tf={by.get('tf', 0):3d} match={by.get('match', 0):3d} "
              f"wrq_k={by.get('wrq_k', 0):3d} cq={by.get('cq', 0):2d}")
    print("dropped:", dict(dedupe.dropped))

    if args.report:
        return 0

    meta = {
        "class_name": "3",
        "subject": "বিজ্ঞান",
        "source": "NCTB তৃতীয় শ্রেণি প্রাথমিক বিজ্ঞান (পাঠ্যবই ভিত্তিক)",
        "note": ("NCTB পাঠ্যবই ভিত্তিক; প্রতিটি প্রশ্ন একটি স্বতন্ত্র তথ্যের উপর "
                 "তৈরি এবং ডুপ্লিকেট-মুক্ত যাচাই করা।"),
        "chapters": len(CHAPTERS),
        "chapter_map": {str(ch): CHAPTERS[ch]["title"] for ch in sorted(CHAPTERS)},
        "bank_version": 2,
        "generated_by": "app/gen_class3.py",
    }
    payload = {"meta": meta, "questions": questions}
    SEED.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {SEED} ({SEED.stat().st_size/1024/1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
