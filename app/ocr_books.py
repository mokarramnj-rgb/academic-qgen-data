#!/usr/bin/env python3
"""OCR the remaining Class 3 NCTB books at 150 dpi (chunked, resumable).

150 dpi is plenty for Bengali body text on these PDFs and roughly four times
faster than 300 dpi, which matters for 100+ page illustrated books.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(os.environ.get("NCTB_DIR", "/media/moki/Everything/NCTB_2026/প্রাথমিক ৩য়"))
OUT = ROOT / "data/class3_full_ocr"
TESSDATA = os.environ.get("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/5/tessdata")
CHUNK = 12


def page_count(pdf: Path) -> int:
    res = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
    for line in res.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1])
    raise RuntimeError(f"no page count for {pdf}")


def run(book: str) -> None:
    pdf = SRC / f"{book}.pdf"
    out = OUT / book
    out.mkdir(parents=True, exist_ok=True)
    total = page_count(pdf)
    env = os.environ.copy()
    env["TESSDATA_PREFIX"] = TESSDATA

    start = 1
    while start <= total:
        end = min(start + CHUNK - 1, total)
        stem = out / f"page-{start:03d}"
        todo = [p for p in range(start, end + 1)
                if not (out / f"page-{p:03d}.txt").exists()]
        if todo:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", "-f", str(start), "-l", str(end),
                 str(pdf), str(stem)],
                check=True,
            )
            for img in sorted(out.glob(f"page-{start:03d}*.png")):
                txt = img.with_suffix("")
                subprocess.run(["tesseract", str(img), str(txt), "-l", "ben"],
                               check=True, env=env)
                img.unlink()
        print(f"{book}: {end}/{total}", flush=True)
        start = end + 1


if __name__ == "__main__":
    for book in sys.argv[1:]:
        run(book)
