"""Mine question *style* from an existing corpus (e.g. Satt Academy).

This module extracts patterns only: stem length, archetype frequencies,
answer-position bias, Bloom proxy, distractor length. It never feeds source
text into the generator, so the NCTB content stays the only factual source.

Usage:
    python -m src.style --jsonl data/class8_sample.jsonl --out data/style_profile.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

# Bangla interrogative / structural archetypes. Ordered: first match wins.
ARCHETYPES: list[tuple[str, str, str]] = [
    ("multi_statement", "i/ii/iii statement combination", r"(?m)^\s*i\.|^\s*ii\.|\biii\."),
    ("fill_blank", "fill in the blank", r"শূন্যস্থান|____|_{3,}|\.{3,}"),
    ("difference", "difference / comparison", r"পার্থক্য|তুলনা|পৃথকীকরণ"),
    ("cause", "cause / reason", r"কেন\b|কারণ|কী কারণে"),
    ("calculation", "calculation / measurement", r"হিসাব|নির্ণয়|সমাধান|গণনা|মান কত"),
    ("definition", "definition / meaning", r"সংজ্ঞা|অর্থ|পরিচয়|কী\s*$|কি\s*$"),
    ("quantity", "quantity / number", r"কতটি|কত\b|কয়টি|কয়\b|সংখ্যা"),
    ("person", "person / who", r"\bকে\b|কোন ব্যক্তি|কোন লেখক"),
    ("place", "place / where", r"কোথায়|কোন স্থানে"),
    ("time", "time / when", r"কখন|কোন সালে|কোন বছরে"),
    ("selection", "which one (কোনটি)", r"কোনটি|কোন্‌টি|নিচের কোন|কোন\s*ধরনের"),
    ("correctness", "which is correct", r"সঠিক|অসঠিক|ভুল"),
    ("other", "other", r"."),
]

BLOOM = [
    ("analyze", r"পার্থক্য|তুলনা|বিশ্লেষণ|কারণ ব্যাখ্যা"),
    ("apply", r"হিসাব|নির্ণয়|সমাধান|প্রয়োগ|গণনা"),
    ("understand", r"কেন|কারণ|ব্যাখ্যা|অর্থ|বোঝাও"),
    ("remember", r"কোনটি|কে\b|কখন|কোথায়|সংজ্ঞা|নাম|কত"),
]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def words(text: str) -> list[str]:
    return re.sub(r"[^\w\u0980-\u09FF]+", " ", text).split()


def classify(stem: str) -> tuple[str, str]:
    for aid, _label, pattern in ARCHETYPES:
        if re.search(pattern, stem):
            return aid, _label
    return "other", "other"


def bloom(stem: str) -> str:
    for level, pattern in BLOOM:
        if re.search(pattern, stem):
            return level
    return "remember"


def summarize(rows: list[dict]) -> dict:
    stems = [r["stem"] for r in rows if r.get("stem")]
    options = [o for r in rows for o in r.get("options", [])]

    stem_words = [len(words(s)) for s in stems]
    opt_words = [len(words(o)) for o in options]

    arche = Counter()
    arche_labels: dict[str, str] = {}
    for s in stems:
        aid, label = classify(s)
        arche[aid] += 1
        arche_labels[aid] = label

    answered = [r for r in rows if r.get("answer_index") in (1, 2, 3, 4)]
    pos = Counter(r["answer_index"] for r in answered)
    n = len(answered) or 1

    tags = Counter(t for r in rows for t in r.get("tags", []))

    def stats(values: list[int]) -> dict:
        if not values:
            return {"mean": 0, "p50": 0, "p90": 0, "max": 0}
        return {
            "mean": round(statistics.mean(values), 1),
            "p50": statistics.median(values),
            "p90": sorted(values)[max(0, int(len(values) * 0.9) - 1)],
            "max": max(values),
        }

    return {
        "corpus": {
            "n": len(rows),
            "with_answer": len(answered),
            "answer_coverage": round(len(answered) / (len(rows) or 1), 2),
            "option_count_mode": Counter(len(r.get("options", [])) for r in rows).most_common(1)[0][0],
        },
        "stem_words": stats(stem_words),
        "option_words": stats(opt_words),
        "answer_position_share": {
            str(k): round(v / n, 2) for k, v in sorted(pos.items())
        },
        "archetypes": [
            {
                "id": aid,
                "label": arche_labels[aid],
                "count": c,
                "share": round(c / (len(stems) or 1), 2),
            }
            for aid, c in arche.most_common()
        ],
        "bloom_proxy": {
            k: round(v / (len(stems) or 1), 2)
            for k, v in Counter(bloom(s) for s in stems).most_common()
        },
        "top_tags": [{"tag": t, "count": c} for t, c in tags.most_common(15)],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build a question-style profile.")
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    profile = summarize(load(args.jsonl))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"style profile -> {args.out}")
    print(f"  questions: {profile['corpus']['n']}  answered: {profile['corpus']['with_answer']}")
    print("  archetypes:", ", ".join(f"{a['id']}={a['share']}" for a in profile["archetypes"][:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
