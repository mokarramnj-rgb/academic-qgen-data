# Continuous question bank expansion

Target: **150 MCQ + 15 জ্ঞানমূলক + 15 অনুধাবনমূলক + 20 সৃজনশীল per chapter** (Class 8 Science, 14 chapters = 2800).

- Resumable/idempotent generator: `app/expand_bank.py` (fills only missing items, dedupes, rebuilds the app).
- Seed: `app/seed/class8_science_all.json` → bundled into `app/question-paper-studio.html`.
- NCTB OCR source (for verification/future refinement): `data/nctb8_ocr/p001-p162.txt`.
- Rule: NCTB facts only; Satt Academy style reference only (no wording reused).

Run anytime to continue/update:
```bash
cd /home/moki/academic-qgen && python3 app/expand_bank.py
```
Increase `TARGETS` in `app/expand_bank.py` for even larger banks, then re-run.
