#!/usr/bin/env python3
"""Clean and segment NCTB Class 3 OCR page text into candidate sentences.

The OCR output of the NCTB PDFs interleaves real prose with page furniture
(page numbers, exercise blanks, decorative noise).  This module keeps only
lines that look like Bengali prose so later stages can mine facts.

    python3 app/c3ocr.py                 # rebuild data/c3_text/<book>.txt
    python3 app/c3ocr.py --stats         # sentence counts per book
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OCR_DIR = ROOT.parent / "data" / "class3_full_ocr"
OUT_DIR = ROOT.parent / "data" / "c3_text"

BENGALI = r"\u0980-\u09FF"
BN_DIGITS = "০১২৩৪৫৬৭৮৯"

# Words/patterns that mark page furniture rather than content.
NOISE_PAT = re.compile(
    r"(শিক্ষাবর্ষ|পাঠ্যবই|পরিবেশ|প্রকাশিত|মুদ্রণ|মূল্য|বোর্ড, বাংলাদেশ|"
    r"জাতীয় শিক্ষাক্রম|সকল অধিকার|প্রথম প্রকাশ|পুনর্মুদ্রণ|ISBN)",
)

# A usable prose line: mostly Bengali letters, few odd symbols.
LETTER = re.compile(rf"[{BENGALI}]")
SENT_SPLIT = re.compile(r"(?<=[।?!])\s+")


def is_bengali_letter(ch: str) -> bool:
    return "\u0980" <= ch <= "\u09ff"


def line_is_prose(line: str) -> bool:
    s = line.strip()
    if len(s) < 14:
        return False
    if NOISE_PAT.search(s):
        return False
    letters = sum(1 for c in s if is_bengali_letter(c))
    if letters < 10:
        return False
    # Reject dot-leader fill-in-the-blank rows and dotted noise.
    if s.count(".") > 4 or "…" in s:
        return False
    # Reject pages of digits (Bengali or ASCII) or symbols.
    weird = sum(1 for c in s if not (is_bengali_letter(c) or c in " ,।?!-‘’\"'" or c.isdigit() or c in BN_DIGITS))
    if weird > max(3, len(s) * 0.12):
        return False
    return True


def clean_line(line: str) -> str:
    s = line.replace("\u09e4", "।")          # OCR danda artifact
    s = s.replace("\u0964", "।")             # Devanagari danda
    s = re.sub(rf"[^\S\n]+", " ", s)         # collapse spaces
    s = re.sub(r"\s*।\s*", "। ", s)
    s = re.sub(r"[|_=~^`<>\[\]{}]+", " ", s)
    s = re.sub(r"\.{2,}", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line_is_prose(line):
            continue
        for piece in SENT_SPLIT.split(line):
            p = piece.strip(" ,;")
            if len(p) < 14:
                continue
            if not p.endswith(("।", "?", "!")):
                p += "।"
            out.append(p)
    return out


def book_dirs() -> dict[str, Path]:
    return {p.name: p for p in sorted(OCR_DIR.iterdir()) if p.is_dir()}


def build(book: str, src: Path) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    pages = sorted(src.glob("page-*.txt"))
    for page in pages:
        for s in sentences(page.read_text(encoding="utf-8", errors="replace")):
            key = re.sub(r"\s+", " ", s)
            if key in seen:
                continue
            seen.add(key)
            result.append(s)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--book", help="only this book")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    books = book_dirs()
    if args.book:
        books = {args.book: books[args.book]}

    total = 0
    for name, src in books.items():
        sents = build(name, src)
        total += len(sents)
        if not args.stats:
            (OUT_DIR / f"{name}.txt").write_text("\n".join(sents) + "\n", encoding="utf-8")
        print(f"{name:28s} pages={len(list(src.glob('page-*.txt'))):4d} sentences={len(sents):5d}")
    print(f"{'total':28s} sentences={total:5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
