import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def extract(pdf_path, output_dir):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # We will use pdftoppm to get images and then tesseract for OCR
    # Processing in batches
    base_name = pdf_path.stem
    print(f"Extracting {base_name}...")
    
    # Extract images
    cmd = ["pdftoppm", "-png", "-r", "300", str(pdf_path), str(output_dir / base_name)]
    subprocess.run(cmd, check=True)
    
    # OCR images
    for img_file in sorted((output_dir).glob(f"{base_name}-*.png")):
        print(f"OCR: {img_file.name}")
        txt_file = output_dir / f"{img_file.stem}.txt"
        # Using Bengali language for OCR
        subprocess.run(["tesseract", str(img_file), str(txt_file.with_suffix("")), "-l", "ben"], check=True)

if __name__ == "__main__":
    nctb = Path(os.environ.get("NCTB_DIR", "/media/moki/Everything/NCTB_2026/প্রাথমিক ৩য়"))
    pdf = nctb / "প্রাথমিক বিজ্ঞান.pdf"
    extract(pdf, ROOT / "data/ocr_science")
