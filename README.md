# Academic Question AI (Bangladesh, Class 3–10)

Two corpora, two jobs:

| Corpus | Role | Never used for |
|---|---|---|
| **Satt Academy** | *Style reference*: how many ways a topic can be asked, stem length, option shape, answer-position bias, archetype mix | facts, wording, training |
| **NCTB textbooks** | *Content source*: the only place facts come from | style |

The generator reads an NCTB chapter, conditions on a mined style profile, and writes new
Bangla MCQs that are validated before entering the item bank. A prerequisite graph + SM-2
scheduler then turns the bank into a step-by-step study plan.

```
NCTB PDF ──► pdftotext ──► chapters ───► chunks ─┐
                                             ├──► generator ──► validator ──► item bank
Satt questions ──► style profile ───────────────┘                               │
                                                                             ▼
                                                                   prerequisite DAG + SM-2 planner
```

---

## 1. Source audit (2026-11-08)

| Source | Public? | Content | Class 1–10? | Blocker |
|---|---|---|---|---|
| `sattacademy.com` | Yes, server-rendered | Large MCQ + CQ bank | **3–10** (no 1–2) | `robots.txt` blocks `?page=` |
| `10minuteschool.com` | Yes, client-rendered | Course products / notes landing pages | 5–12 products | Not a public question bank; class-8 page is a stub |
| `eproshnobank.com` | No | Question-generator SaaS | n/a | Next.js soft-404; content behind login/payment |

**Satt counts** (class landing pages):

| Class | MCQs | Pages | Subjects |
|------|:---------:|:---------:|:---------:|
| 3 | 1,982 | 133 | 11 |
| 4 | 2,614 | 175 | 11 |
| 5 | 3,084 | 206 | 8 |
| 6 | 10,132 | 676 | 18 |
| 7 | 10,359 | 691 | 18 |
| 8 | 15,720 | 1,048 | 22 |
| 8 (Dakhil) | 20 | 2 | 2 |
| 9–10 | 110,317 | 7,355 | 33 |
| 9–10 (Dakhil) | 518 | 35 | 14 |

**Class 3–10 ≈ 154,700 MCQs**, plus a CQ bank (class 8 ~17.8k CQ). No class 1–2.

`robots.txt` disallows `/*?page=*` and `/*&page=*`, so bulk crawling is off-limits.
The parser therefore works on **saved pages** or single allowed URLs, and a small sample
is enough for style mining — you do not need all 154k items for a style profile.

---

## 2. What is implemented

| File | Purpose |
|---|---|---|
| `src/satt.py` | Offline/robots-checked parser for Satt question pages |
| `src/style.py` | Mines archetypes, stem/option length, answer-position bias, Bloom proxy |
| `src/nctb.py` | PDF → pages → chapter detection → overlapping chunks |
| `src/generate.py` | Style-conditioned MCQ generation + validation + dedupe |
| `src/plan.py` | Prerequisite depth ordering + SM-2 study plan |
| `src/schema.sql` | Questions, chunks, curriculum nodes, items, attempts, schedule |
| `src/db.py` | SQLite ingest + stats |

### Class 3 bank (2026-11-11)

All nine NCTB Class 3 subjects are generated from curated fact bases in
`app/facts_c3/` by `app/gen_c3.py`:

| Subject | Code | Chapters | Questions |
|---|---|:---:|:---------:|
| প্রাথমিক বিজ্ঞান | `sci` | 11 | 2,894 |
| আমার বাংলা বই | `ban` | 14 | 2,350 |
| English For Today | `eng` | 8 | 2,116 |
| প্রাথমিক গণিত | `math` | 13 | 3,317 |
| ইসলাম শিক্ষা | `isl` | 5 | 1,224 |
| হিন্দুধর্ম শিক্ষা | `hin` | 5 | 1,081 |
| বৌদ্ধধর্ম শিক্ষা | `bud` | 9 | 1,617 |
| খ্রিষ্টধর্ম শিক্ষা | `chr` | 5 | 1,239 |
| বাংলাদেশ ও বিশ্বপরিচয় | `bws` | 12 | 1,699 |
| **Total** | | **74** | **17,561** |

`classes/class-3.json` is the combined bank; `app/seed/class3_<code>_all.json`
holds one file per subject. See `HANDOFF.md` for the current state and the
unfinished work (publishing the bank, quality review, Class 4–10).

### Verified on this machine

- Satt class-8 page → 15 questions parsed, 9 with answers.
- Style profile → 4 options/item, mean stem 11.4 words, answer positions 11/22/44/22%.
- NCTB class-7 Bangla PDF (144 pages) → 355 chunks, chapters 1–7 detected.
- `pdftotext` extracts Bangla well; one page uses a legacy ASCII font and produces
gibberish, so chunk filtering by script ratio is recommended (roadmap).
- Bengali OCR uses `tesseract-ocr-ben` (installed here); scanned PDFs are
distributed via `data/c3_text/` and also available in `data/class3_full_ocr/` for
Math. The fact base itself was written from the textbook structure (13 chapters),
not from the OCR dump, so OCR is reference material only.

- `app/extract_all.py` (done 2026-11-11) now handles both: `TEXT_LAYER`
routes `English For Today.pdf` through `pdftotext`, `OCR_DPI` lowers the
162-page Math book to 150 dpi, and `SKIP` ignores the duplicate scan.
A fresh checkout can rebuild both corpora with `python3 app/extract_all.py`.

- **Class 3 – all subjects expanded**
  - `python3 app/check_facts.py` → total problems: 0 for every subject
    (warnings are pre-existing tolerated items: repeated group-rights, short
    arithmetic facts, non-noun keys)
  - `python3 gen_c3.py` → 17,561 questions, 0 rejected; wrote
    `classes/class-3.json` (10.38 MB) and per-subject `app/seed/class3_*_all.json`
  - `python3 -m tests.test_pipeline` → ok
  - Extended `gen_c3.py` with four question types per chapter (fill‑in‑definition,
    definition→MCQ, pair‑match MCQ, term↔definition match sets); script‑aware
    `clean_text()` (English/Math no longer falsely rejected); Bengali digits for
    Bengali/Math, ASCII digits for English.

- Quality pass on MCQs:
  - Fixed pair‑match MCQ distractor selection to reject containment (answer inside
    distractor or vice‑versa) and skip trivial identity matches.
  - bws and eng MCQs now have 0 containment issues (previously 6 and 4).

### How to run

```bash
cd app
python3 gen_c3.py          # regenerate the combined class‑3 bank
python3 gen_c3.py --report  # show per‑subject stats
python3 -m tests.test_pipeline  # validation suite
```

For Class 4–10: add `app/facts_c<N>/` modules and a `gen_c<N>.py` clone.

---

## 3. Quickstart

1. Install environment (system packages, tesseract-ocr-ben, pdftotext, python3).
2. Run `python3 app/extract_all.py` to build the OCR/text corpora.
3. Manually edit one of the `app/facts_c3/*.py` files to add a fact; run
   `python3 app/check_facts.py <code>` to confirm (0 problems required).
4. Run `python3 gen_c3.py` to regenerate the bank.

---

## 4. NCTB notes

- `sattacademy.com` parses: class landing page → `<ul class="question-list">` →
  `<li>` items → `<a>` links → page fetch → `class="question-body"` + `class="answer"`.
- `10minuteschool.com` is a product catalog; no public bank; page uses JavaScript.
- `eproshnobank.com` is behind login/payment; not used.
- **OCR**: Math scanned PDFs → `tesseract -l ben data/class3_full_ocr/ ...`
  → `data/c3_text/প্রাথমিক গণিত.txt`.
- **English**: `data/c3_text/English For Today.txt` (6, trespass lines) from
  `pdftotext` of the textbook.

`app/extract_all.py` is the one‑stop rebuild for both corpora.

---

## 5. Data model

- **subjects.json**: NCTB books (`code`, `book`, `script`).
- **classes/class-<n>.json**: per‑class combined bank.
- **app/seed/class3_<code>_all.json**: subject bank snapshots.
- **questions** table: id, type, stem, options, answer_index, answer_text,
  subject_code, chapter, bloom, difficulty, marks.
- **chunks** table: id, text, source, script, chunk_index.
- **curriculum_nodes**: mapping chapter titles to sequences.
- **items**: user progress per question; **attempts**: history; **schedule**:
  SM‑2 intervals.

- Each question carries `subject_code`, so `chapter_map["sci:1"]` can be resolved.
- Script validation:
  - `bn`: strict Bengali‑only filter.
  - `en`: English punctuation + ASCII digits (ASCII underscores for fill‑in‑def).
  - `math`: Bengali digits + arithmetic symbols (π, ≠, ≤) – not rejected by
    `clean_text`.

---

## 6. Guardrails

- Never commit tokens (`/tmp/opencode/.gh_token`), PATs, or downloaded PDFs.
- Facts are `(statement, key)`; `key` must appear verbatim in `statement`,
  otherwise the blank is skipped.
- `tf_false` entries must be genuinely false; they are the only false statements
the generator trusts.
- `clean_text` rejects Latin letters for Bengali subjects; English/Math use
"script": "en" / "math".
- `gen_c3.py` uses a seeded RNG; reruns produce the same bank.
- Per‑chapter MCQ / fill‑in‑definition / TF / CQ must stay ≥ 1 (all 74 chapters
meet coverage). Run `python3 gen_c3.py --report` and `python3 -m tests.test_pipeline`

---

## 7. Roadmap

1. **Publish Class 3** → GitHub PAT needed.
2. **Class 4–10** → `app/facts_c<N>/` pattern.
3. **Style mining**: more Satt classes → finer archetypes.
4. **Chunk detection**: better script ratio filter for Bangla.
5. Männer:
   - `src/plan.py`: SM‑2 scheduler (next studied item).
   - `src/db.py`: SQLite backup.
   - `src/generate.py`: smarter distractors (semantic similarity).
   - `src/satt.py`: full CQ support.
6. **App integration**: publish via `question-paper-studio`.
7. **Review**: external human QA on MCQ plausibility (especially bws, eng).