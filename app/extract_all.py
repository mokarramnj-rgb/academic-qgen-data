import os
import subprocess
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent.parent
TESSDATA = os.environ.get("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/5/tessdata")

def extract_pdf(pdf_path, base_output_dir):
    pdf_path = Path(pdf_path)
    book_name = pdf_path.stem
    output_dir = Path(base_output_dir) / book_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"--- Processing {book_name} ---")
    
    # 1. Convert PDF to Images
    img_prefix = str(output_dir / "page")
    print(f"Converting to images...")
    subprocess.run(["pdftoppm", "-png", "-r", "300", str(pdf_path), img_prefix], check=True)
    
    # 2. OCR Images
    images = sorted(output_dir.glob("page-*.png"))
    print(f"Found {len(images)} pages. Starting OCR...")
    
    env = os.environ.copy()
    env['TESSDATA_PREFIX'] = TESSDATA
    
    for i, img in enumerate(images):
        txt_output = img.with_suffix("")
        # print(f"[{i+1}/{len(images)}] OCR: {img.name}")
        subprocess.run(["tesseract", str(img), str(txt_output), "-l", "ben"], check=True, env=env)
        # Remove image to save space
        img.unlink()

if __name__ == "__main__":
    source_dir = os.environ.get("NCTB_DIR", "/media/moki/Everything/NCTB_2026/প্রাথমিক ৩য়")
    base_out = ROOT / "data/class3_full_ocr"
    
    exclude = ["English For Today.pdf", "প্রাথমিক গণিত.pdf", "প্রাথমিক গণিত (2).pdf"]
    
    pdfs = [f for f in os.listdir(source_dir) if f.endswith(".pdf") and f not in exclude]
    
    for pdf in sorted(pdfs):
        extract_pdf(os.path.join(source_dir, pdf), base_out)
