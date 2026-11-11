"""OCR the NCTB Class 3 textbooks into data/class3_full_ocr/<book>/.

Bengali books are rasterised and OCR'd with Tesseract.  English For Today
already carries a text layer, so it is read with pdftotext instead.  The
Mathematics book is rasterised at a lower dpi because it is 162 pages of
mostly numerals and diagrams.

    python3 app/extract_all.py
    python3 app/c3ocr.py          # clean + segment into data/c3_text/<book>.txt
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESSDATA = os.environ.get("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/5/tessdata")

# Books that already have a text layer: read them, do not OCR them.
TEXT_LAYER = {"English For Today.pdf"}

# Per-book OCR resolution (default 300 dpi).
OCR_DPI = {"প্রাথমিক গণিত.pdf": 150}

# Duplicate scans of a book that is already processed.
SKIP = {"প্রাথমিক গণিত (2).pdf"}


def extract_pdf(pdf_path, base_output_dir, dpi=300):
    pdf_path = Path(pdf_path)
    book_name = pdf_path.stem
    output_dir = Path(base_output_dir) / book_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"--- Processing {book_name} (OCR {dpi} dpi) ---")

    # 1. Convert PDF to Images
    img_prefix = str(output_dir / "page")
    print("Converting to images...")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), img_prefix],
                   check=True)

    # 2. OCR Images
    images = sorted(output_dir.glob("page-*.png"))
    print(f"Found {len(images)} pages. Starting OCR...")

    env = os.environ.copy()
    env["TESSDATA_PREFIX"] = TESSDATA

    for img in images:
        txt_output = img.with_suffix("")
        subprocess.run(["tesseract", str(img), str(txt_output), "-l", "ben"],
                       check=True, env=env)
        img.unlink()


def extract_text_layer(pdf_path, text_output_dir):
    """Books with a real text layer: pdftotext per page, one file per page."""
    pdf_path = Path(pdf_path)
    book_name = pdf_path.stem
    output_dir = Path(text_output_dir) / book_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"--- Processing {book_name} (text layer) ---")
    pages = subprocess.run(["pdfinfo", str(pdf_path)], check=True,
                           capture_output=True, text=True).stdout
    count = next((int(line.split()[1]) for line in pages.splitlines()
                  if line.startswith("Pages:")), 0)
    for page in range(1, count + 1):
        out = output_dir / f"page-{page:03d}.txt"
        text = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), str(pdf_path), "-"],
            check=True, capture_output=True, text=True).stdout
        out.write_text(text, encoding="utf-8")
    print(f"Wrote {count} pages to {output_dir}")


if __name__ == "__main__":
    source_dir = os.environ.get(
        "NCTB_DIR", "/media/moki/Everything/NCTB_2026/প্রাথমিক ৩য়")
    base_out = ROOT / "data/class3_full_ocr"

    pdfs = [f for f in os.listdir(source_dir)
            if f.endswith(".pdf") and f not in SKIP]

    for pdf in sorted(pdfs):
        path = os.path.join(source_dir, pdf)
        if pdf in TEXT_LAYER:
            extract_text_layer(path, base_out)
        else:
            extract_pdf(path, base_out, dpi=OCR_DPI.get(pdf, 300))
