"""NCTB textbook ingestion: PDF -> pages -> chapter-aware chunks.

Requires poppler's `pdftotext` (already installed on this machine). For scanned
PDFs with no text layer, install Bengali OCR:
    sudo pacman -S tesseract tesseract-data-ben
then pass --ocr.

Usage:
    python -m src.nctb --pdf data/raw/class8-science.pdf \
        --class 8 --subject science --out data/chunks.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
CHAPTER_RE = re.compile(r"(?:অধ্যায়|অধ্যায়)\s*[-–—:]*\s*([০-৯0-9]+)")


def extract_text(pdf: Path, ocr: bool = False) -> str:
    if shutil.which("pdftotext") is None:
        raise SystemExit("pdftotext not found. Install poppler.")
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    if len(out.strip()) < 200:
        if ocr or _has_ben_ocr():
            print("text layer empty/small; using OCR...", file=sys.stderr)
            return extract_ocr(pdf)
    return out


def _has_ben_ocr() -> bool:
    if shutil.which("tesseract") is None:
        return False
    env = None
    prefix = Path.home() / ".local/share/tessdata"
    if prefix.exists():
        import os
        env = {**os.environ, "TESSDATA_PREFIX": str(prefix)}
    try:
        langs = subprocess.run(
            ["tesseract", "--list-langs"], capture_output=True, text=True, env=env,
        ).stdout
    except Exception:
        return False
    return "ben" in langs.split()


def extract_ocr(pdf: Path) -> str:
    """Fallback for scanned PDFs. Needs tesseract + ben traineddata."""
    if shutil.which("tesseract") is None or shutil.which("pdftoppm") is None:
        raise SystemExit("tesseract/pdftoppm not found for OCR")
    env = None
    prefix = Path.home() / ".local/share/tessdata"
    if prefix.exists():
        import os
        env = {**os.environ, "TESSDATA_PREFIX": str(prefix)}
    langs = subprocess.run(
        ["tesseract", "--list-langs"], capture_output=True, text=True, env=env,
    ).stdout
    if "ben" not in langs.split():
        raise SystemExit("Bengali OCR data missing: install tesseract-data-ben")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        subprocess.run(
            ["pdftoppm", "-r", "180", "-png", str(pdf), str(tmp / "p")],
            check=True, capture_output=True,
        )
        parts = []
        for img in sorted(tmp.glob("p-*.png")):
            txt = subprocess.run(
                ["tesseract", str(img), "stdout", "-l", "ben", "--psm", "6"],
                capture_output=True, text=True, env=env,
            ).stdout
            parts.append(txt)
        return "\f".join(parts)


def page_chapter(text: str) -> int | None:
    m = CHAPTER_RE.search(text)
    return int(m.group(1).translate(BENGALI_DIGITS)) if m else None


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text)
    parts = re.split(r"(?<=[।!?])\s+|\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_pages(pages: list[str], target: int = 1200, overlap: int = 150) -> list[dict]:
    chunks: list[dict] = []
    chapter = 0
    for pno, page in enumerate(pages, 1):
        found = page_chapter(page)
        if found:
            chapter = found
        sentences = split_sentences(page)
        buf = ""
        for sent in sentences:
            if len(buf) + len(sent) + 1 > target and len(buf) >= target // 2:
                chunks.append({"page": pno, "chapter": chapter, "text": buf.strip()})
                buf = buf[-overlap:] + " " if overlap else ""
            buf += sent + " "
        if len(buf.strip()) > 80:
            chunks.append({"page": pno, "chapter": chapter, "text": buf.strip()})
    return chunks


def ingest(pdf: Path, class_name: str, subject: str,
           target: int, overlap: int) -> list[dict]:
    raw = extract_text(pdf)
    pages = raw.split("\f")
    rows = []
    for i, c in enumerate(chunk_pages(pages, target, overlap)):
        cid = hashlib.sha1(f"{pdf.name}:{i}:{c['text'][:80]}".encode()).hexdigest()[:16]
        rows.append({
            "id": cid,
            "doc": pdf.name,
            "class_name": class_name,
            "subject": subject,
            "chapter": str(c["chapter"]),
            "page": c["page"],
            "text": c["text"],
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chunk an NCTB textbook PDF.")
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--class", dest="class_name", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--target", type=int, default=1200)
    ap.add_argument("--overlap", type=int, default=150)
    ap.add_argument("--txt", type=Path, help="also save raw extracted text")
    args = ap.parse_args(argv)

    rows = ingest(args.pdf, args.class_name, args.subject, args.target, args.overlap)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    if args.txt:
        args.txt.write_text(extract_text(args.pdf), encoding="utf-8")

    chapters = sorted({r["chapter"] for r in rows})
    print(f"{len(rows)} chunks -> {args.out}")
    print(f"  pages: {max(r['page'] for r in rows)}  chapters detected: {chapters}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
