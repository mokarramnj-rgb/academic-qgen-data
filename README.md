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
NCTB PDF ──► pdftotext ──► chapters ──► chunks ─┐
                                                ├──► generator ──► validator ──► item bank
Satt questions ──► style profile ───────────────┘                                  │
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
|---|---:|---:|---:|
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
|---|---|
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
|---|---|---:|---:|
| প্রাথমিক বিজ্ঞান | `sci` | 11 | 1,781 |
| আমার বাংলা বই | `ban` | 14 | 1,174 |
| English For Today | `eng` | 8 | 342 |
| প্রাথমিক গণিত | `math` | 13 | 484 |
| ইসলাম শিক্ষা | `isl` | 5 | 857 |
| হিন্দুধর্ম শিক্ষা | `hin` | 5 | 687 |
| বৌদ্ধধর্ম শিক্ষা | `bud` | 9 | 718 |
| খ্রিষ্টধর্ম শিক্ষা | `chr` | 5 | 685 |
| বাংলাদেশ ও বিশ্বপরিচয় | `bws` | 4 | 262 |
| **Total** | | **74** | **6,990** |

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
  rasterised at 300 dpi (150 dpi for the 162-page Mathematics book) and OCR'd.
  `English For Today` has a text layer and is read with `pdftotext`.

---

## 3. Quickstart

```bash
cd academic-qgen

# 1. Style profile from a saved Satt page (offline)
python3 -m src.satt --html data/raw/class8.html --class 8 --out data/class8_sample.jsonl
python3 -m src.style --jsonl data/class8_sample.jsonl --out data/style_profile.json

# 2. NCTB chapter ingestion
python3 -m src.nctb --pdf data/raw/class8-science.pdf \
  --class 8 --subject science --out data/chunks.jsonl --txt data/raw/class8-science.txt

# 3. Generate from a chapter, conditioned on style
export OPENAI_BASE_URL=https://opencode.ai/inference/openai/v1
export OPENAI_API_KEY=...          # or Ollama: http://127.0.0.1:11434/v1
export MODEL=deepseek-v4.1-flash-free
python3 -m src.generate \
  --ref data/raw/science-ch1.txt \
  --class 8 --subject science --chapter 1 \
  --n 10 --style data/style_profile.json --verify --out data/generated.jsonl

# 4. Study plan
python3 -m src.db --jsonl data/class8_sample.jsonl --db data/qbank.sqlite
python3 -m src.plan --db data/qbank.sqlite --user demo --weeks 4 \
  --curriculum data/curriculum.example.json
```

`make sample`, `make style`, `make test` are wired.

---

## 4. NCTB notes

- Download textbooks from `https://nctb.gov.bd/` → *পাঠ্যপুস্তক* → year → level.
  The site's TLS chain is broken; `curl -k` is needed, but verify the PDFs you download.
- Many PDFs have a real text layer (good). Scanned ones need Bengali OCR.
- Chapter headings are recognised as `অধ্যায় <n>` (Bangla or ASCII digits). Pages before
  the first heading go to chapter `0`.
- Keep the source page number on every chunk so generated items can cite it.

---

## 5. Data model

- `questions` — source items for style mining only
- `chunks` — NCTB passages with class/subject/chapter/page
- `nodes` — curriculum DAG (prerequisites)
- `items` — generated MCQs (`draft` → `approved`/`rejected`)
- `attempts` — per-user answers
- `schedule` — SM-2 state per user/node

---

## 6. Guardrails

- **Facts:** only from the NCTB reference. The validator rejects stems with >50% 5-word-gram
  overlap with the reference, and an optional second pass re-answers each item.
- **Style:** Satt shapes the distribution; the prompt forbids copying its wording.
- **Copyright:** Satt questions are not redistributed or trained on. NCTB textbooks are
  freely distributed by the government; still cite source and page.
- **Human review:** items default to `draft`; nothing auto-publishes.

---

## 7. Roadmap

| Phase | Deliverable |
|---|---|
| 0 (now) | Parser, style miner, NCTB chunker, generator, planner |
| 1 | One full subject end-to-end (Class 8 Science), Bangla PDF cleanup + script filter |
| 2 | Distractor taxonomy + answerability check (second model), Bloom classifier |
| 3 | Web UI: quiz runner, teacher review queue, PDF/OMR export |
| 4 | Adaptive engine: mastery estimation, prerequisite-aware item selection |
| 5 | Class 1–2 coverage from NCTB primary books (Satt has none) |
