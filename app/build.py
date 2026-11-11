#!/usr/bin/env python3
"""Bundle src/ into one portable HTML file.

    python3 app/build.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
SEED = ROOT / "seed" / "class8_science_all.json"
OUT = ROOT / "question-paper-studio.html"

JS_PARTS = ["01-core.js", "02-paper.js", "03-ui.js", "04-init.js"]


def _compact_seed(data: dict) -> str:
    meta = dict(data.get("meta") or {})
    cmap = meta.get("chapter_map") or meta.get("cm") or {}
    base = {
        "class_name": meta.get("class_name", "8"),
        "subject": meta.get("subject", "বিজ্ঞান"),
        "source": meta.get("source", "NCTB"),
    }
    questions = []
    for q in data.get("questions") or []:
        n = dict(q)
        for k, v in base.items():
            if n.get(k) == v:
                n.pop(k, None)
        ch = str(n.get("chapter", ""))
        if cmap.get(ch) and n.get("chapter_title") == cmap.get(ch):
            n.pop("chapter_title", None)
        for k in ("stimulus", "subquestions", "explanation", "options"):
            if not n.get(k):
                n.pop(k, None)
        if not n.get("answer_index") and n.get("answer_index") != 0:
            n.pop("answer_index", None)
        questions.append(n)
    meta_out = {k: v for k, v in meta.items() if k not in ("chapter_map",)}
    meta_out["cm"] = cmap
    return json.dumps({"meta": meta_out, "questions": questions}, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    template = (SRC / "index.template.html").read_text(encoding="utf-8")
    css = (SRC / "style.css").read_text(encoding="utf-8").strip()
    js = "\n\n".join((SRC / name).read_text(encoding="utf-8").strip() for name in JS_PARTS)

    data = json.loads(SEED.read_text(encoding="utf-8"))
    seed_text = _compact_seed(data)
    if "</script" in seed_text.lower() or "</script" in js.lower():
        raise SystemExit("refusing to inline: found </script> in JS or seed")

    html = (
        template
        .replace("/*__CSS__*/", css)
        .replace("/*__JS__*/", js)
        .replace("__SEED__", seed_text)
    )

    OUT.write_text(html, encoding="utf-8")

    questions = len(data.get("questions") or [])
    size_kb = OUT.stat().st_size / 1024
    size_mb = size_kb / 1024
    print(f"built {OUT.name}: {size_kb:.1f} KB ({size_mb:.2f} MB), {questions} seeded questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
