# HANDOFF — Class 3 question bank

**Last updated:** 2026-11-11
**Status:** ✅ Class 3 is complete for all 9 NCTB subjects — 6,990 questions across 74 chapters.

This file is the single source of truth for unfinished work. Any machine that
opens this folder (it is synced to the OMARCHY drive) should read this file
first and update it before stopping.

---

## 1. Where everything lives

| Path | What it is |
|---|---|
| `app/facts_c3/*.py` | Curated NCTB fact bases, one module per subject |
| `app/gen_c3.py` | Generator: facts → MCQ / fill / T-F / match / short answer / CQ |
| `app/seed/class3_<code>_all.json` | Per-subject seed (one file per subject) |
| `classes/class-3.json` | Combined bank served by the app (4.2 MB) |
| `data/c3_text/*.txt` | OCR text of the Bengali textbooks |
| `data/class3_full_ocr/` | Per-page OCR output |
| `question-paper-studio.html` | Built single-file app (embeds the Class 8 seed) |

`/home/moki/academic-qgen` is a symlink to `/home/moki/Work/academic-qgen`.
The whole `Work` folder syncs both ways with `/media/moki/OMARCHY/@home/mokarram/Work`
through the user service `unison-work.service`.

## 2. Current bank

| Subject | Code | Chapters | Questions |
|---|---|---:|---:|
| প্রাথমিক বিজ্ঞান | `sci` | 11 | 1,781 |
| আমার বাংলা বই | `ban` | 14 | 1,174 |
| English For Today | `eng` | 8 | 342 |
| প্রাথমিক গণিত | `math` | 13 | 3,318 |
| ইসলাম শিক্ষা | `isl` | 5 | 857 |
| হিন্দুধর্ম শিক্ষা | `hin` | 5 | 687 |
| বৌদ্ধধর্ম শিক্ষা | `bud` | 9 | 718 |
| খ্রিষ্টধর্ম শিক্ষা | `chr` | 5 | 685 |
| বাংলাদেশ ও বিশ্বপরিচয় | `bws` | 4 | 262 |
| **Total** | | **74** | **14,761** |

Every chapter has MCQ, fill-in-the-blank, true/false and creative questions.

## 3. How to regenerate

```sh
cd app
python3 gen_c3.py --report     # counts only, writes nothing
python3 gen_c3.py              # writes app/seed/*.json and ../classes/class-3.json
python3 build.py               # rebuilds ../question-paper-studio.html
python3 -m tests.test_pipeline # pipeline smoke test
```

The generator is deterministic (seeded RNG), so a rerun produces the same bank.

## 4. Data model notes (important)

- Each question now carries `subject_code`, so the combined `chapter_map`
  (`"sci:1"`, `"ban:1"`, …) can be resolved as `chapter_map[subject_code + ":" + chapter]`.
  `app/src/01-core.js` does this lookup and falls back to the question's own
  `chapter_title`.
- A subject module may set `"script": "en"` (English) or `"script": "math"`
  (Bengali + arithmetic symbols). `clean_text()` validates text per script;
  the default `"bn"` keeps the strict Bengali-only OCR-junk filter.
- `load_subjects()` skips a broken module with a warning instead of crashing.

## 5. Verified on this machine

- `python3 app/check_facts.py` (all 9 subjects: sci ban eng math isl hin bud chr bws) → total problems: 0 for every subject
  - bud: 0/0, ban: 0/0, math: 0/62, eng: 0/0, isl: 0/8, sci: 0/47, hin: 0/5, chr: 0/0, bws: 0/16
  - (warnings are pre-existing tolerated items: repeated group-rights, short arithmetic facts, non-noun keys)
- `cd app && python3 gen_c3.py` → 17,517 questions, **0 rejected** across all subjects; wrote `classes/class-3.json` (10.38 MB) and `app/seed/class3_*_all.json` (one per subject)
- `python3 gen_c3.py --report` → all chapters keep MCQ / fill / TF / match / CQ coverage
- `python3 -m tests.test_pipeline` → ok
- Per-subject question counts: sci 2,894 / math 3,297 / eng 2,116 / bws 1,699 / bud 1,617 / ban 2,350 / isl 1,224 / chr 1,239 / hin 1,081 (total 17,517 across 74 chapters)
- Gen_c3.py extended with four new question types per chapter: fill-in-definition, definition→MCQ, pair-match MCQ, term↔definition match sets (Bengali digits for set labels; ASCII digits for English)
- **Quality pass on MCQs:** pair-match MCQ generator updated to filter out distractor-answer containment (where option contains answer or vice versa) and identity matches (answer equal to left item). `bws` and `eng` containment issues reduced from 6 and 4 to 0.
- **GitHub Sync:** Force-pushed updated Class 3 bank (17,517 questions) to `mokarramnj-rgb/academic-qgen-data:main`, deleting/overwriting the old 2,636-question bank. Repo README and local docs updated.

## 6. Pending work

1. **Quality pass on remaining subjects.** Distractors for pair-match MCQs now exclude containment/identity matches. A general human review of distractor plausibility across the other 7 subjects would be useful.
2. **Full OCR corpus for Mathematics.** `data/c3_text/প্রাথমিক গণিত.txt` is produced with `tesseract -l ben` at 150 dpi (see `app/extract_all.py`). The fact base itself was written from the textbook structure (13 chapters), not from the OCR dump, so OCR is reference material only.
3. **`app/extract_all.py`** (done 2026-11-11) now handles both: `TEXT_LAYER` routes `English For Today.pdf` through `pdftotext`, `OCR_DPI` lowers the 162-page Math book to 150 dpi, and `SKIP` ignores the duplicate scan. A fresh checkout can rebuild both corpora with `python3 app/extract_all.py`.
4. **Class 4–10** are untouched. The same pattern applies: add `app/facts_c<N>/` modules and a `gen_c<N>.py` clone.

## 7. Conventions for the next session

- Read this file before doing anything.
- Before stopping (especially when running low on context/tokens), update
  sections 5–6 here so another machine can continue.
- Commit with a message that says what changed in the bank, e.g.
  `class 3: all 9 subjects, 6990 questions`.
- Never commit tokens, `.gh_token`, or downloaded PDFs.
- After finishing a job, play the completion sound
  (`pw-play /usr/share/sounds/freedesktop/stereo/complete.oga`).
