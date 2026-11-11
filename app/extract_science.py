import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESSDATA = os.environ.get("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/5/tessdata")
NCTB = Path(os.environ.get("NCTB_DIR", "/media/moki/Everything/NCTB_2026/প্রাথমিক ৩য়"))

pdf_path = NCTB / "প্রাথমিক বিজ্ঞান.pdf"
output_dir = ROOT / "data/class3_full_ocr/প্রাথমিক বিজ্ঞান"
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Extracting প্রাথমিক বিজ্ঞান...")
subprocess.run(["pdftoppm", "-png", "-r", "300", str(pdf_path), str(output_dir / "page")], check=True)

images = sorted(output_dir.glob("page-*.png"))
print(f"OCR {len(images)} pages...")

env = os.environ.copy()
env['TESSDATA_PREFIX'] = TESSDATA

for img in images:
    txt = img.with_suffix("")
    subprocess.run(["tesseract", str(img), str(txt), "-l", "ben"], check=True, env=env)
    img.unlink()

print("Primary Science OCR complete!")
