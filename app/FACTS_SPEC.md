# How to author a Class 3 fact base (`app/facts_c3/<code>.py`)

The question bank is **generated from a curated fact base**, never from OCR text
directly. One module per textbook. OCR is only the raw material: you read it and
write the fact base by hand, in clean Bengali.

## Files

| code  | textbook                        | cleaned OCR                                |
|-------|---------------------------------|--------------------------------------------|
| `sci` | প্রাথমিক বিজ্ঞান                | `data/c3_text/প্রাথমিক বিজ্ঞান.txt`         |
| `ban` | আমার বাংলা বই                   | `data/c3_text/আমার বাংলা বই.txt`            |
| `isl` | ইসলাম শিক্ষা                    | `data/c3_text/ইসলাম শিক্ষা.txt`             |
| `hin` | হিন্দুধর্ম শিক্ষা                | `data/c3_text/হিন্দুধর্ম শিক্ষা.txt`        |
| `bud` | বৌদ্ধধর্ম শিক্ষা                | `data/c3_text/বৌদ্ধধর্ম শিক্ষা.txt`         |
| `chr` | খ্রিষ্টধর্ম শিক্ষা               | `data/c3_text/খ্রিষ্টধর্ম শিক্ষা.txt`       |
| `bws` | বাংলাদেশ ও বিশ্বপরিচয়          | `data/c3_text/বাংলাদেশ ও বিশ্বপরিচয়.txt`    |

Reference implementation: `app/facts_c3/sci.py` (science, 11 chapters, already
finished). Read it first — copy its style exactly.

## Module shape

```python
"""Curated NCTB Class 3 <বই> fact base."""

SUBJECT = {
    "code": "ban",
    "subject": "বাংলা",                     # shown in the app's subject selector
    "book": "আমার বাংলা বই",
    "source": "NCTB তৃতীয় শ্রেণি আমার বাংলা বই (২০২৬)",
    "chapters": {
        1: {
            "title": "অধ্যায়ের নাম",
            "defs": [("শব্দ", "সংজ্ঞা"), ...],
            "facts": [("বাক্য।", "মূল শব্দ"), ...],
            "groups": [("শ্রেণির নাম", [("বাম", "ডান"), ...]), ...],
            "cq": [("উদ্দীপক", [("ক", "প্রশ্ন", 1), ("খ", "প্রশ্ন", 2), ("গ", "প্রশ্ন", 3)], "উত্তর"), ...],
            "terms": ["অতিরিক্ত", "শব্দ", ...],
            "classes": [["বৃক্ষ", "গুল্ম", "বিরুৎ"], ...],
            "tf_false": [("অশুদ্ধ বাক্য।", "সঠিক তথ্য"), ...],
            "qa": [("পাঠ্যবইয়ের প্রশ্ন?", "সংক্ষিপ্ত উত্তর।"), ...],
        },
        ...
    },
}
```

`chapters` keys are `int`, in textbook order.

## Field semantics

* **defs** — `(term, definition)`. `term` is a 1–3 word noun phrase
  (`noun_like`: no verb ending such as করে/হয়/থাকে/যায়/পায়/দেয়/খায়/নয়, and it
  must not start with যে/যা/একটি). `definition` is a full clause **without** the
  final danda. The generator turns this into `"<definition>—এটি কী?"` MCQ plus a
  `জ্ঞানমূলক` short question. Keep it 10–140 characters.
* **facts** — `(statement, key)`. `statement` is one complete textbook sentence
  ending in `।`. `key` is the single most testable word/phrase in it, and it must
  appear **exactly once** and as a whole word (never inside another word).
  The generator blanks `key` for a fill item and an MCQ, and states it for a
  true item.
* **groups** — `(category, [(left, right), ...])`. Used for one-to-one matching.
  Give 4–6 pairs; **the first five pairs must have all-distinct left and
  all-distinct right** values (duplicates are dropped, which shrinks the item).
  Right side is short: 1–4 words.
* **cq** — `(stimulus, subquestions, answer)`. `stimulus` is a 2–3 sentence
  scenario using the chapter's facts (min 30 characters). Labels must be
  `ক, খ, গ, ঘ` in that order with marks `1, 2, 3, 4`. `answer` summarises the
  model answer in one or two clauses.
* **terms** — extra chapter vocabulary used only as distractors. Nouns only.
  Add 6–12 that are *plausible but wrong* (same semantic field).
* **classes** — lists of co-hyponym nouns, used to make MCQ distractors
  plausible (e.g. `["বৃক্ষ", "গুল্ম", "বিরুৎ"]`, `["জ্বিন", "ফেরেশতা", "মানুষ"]`).
  Every member must be a real term of the same kind — never mix a type with an
  example.
* **tf_false** — `(false_statement, correction)`. A grammatically correct
  sentence that is **factually wrong**, expressed by swapping in a real but
  wrong term, or by inverting a real relation. Never built by appending "না".
  `correction` states the true fact. **Write as many of these as there are
  facts** — the generator samples true statements down to match, so the
  true/false section stays balanced.
* **qa** — `(question, answer)` taken from the textbook's own exercise
  questions. Answer in one clause.

## Hard rules (the validator enforces them)

1. Only Bengali script, Bengali digits and `. , ; : ? ! । — ‘ ’ " ' ( ) % -` may
   appear. OCR produces Latin letters and Devanagari (`U+0900–U+097F`); never
   copy them.
2. Every text field must pass `app/clean_text` and be at least 2 Bengali letters.
3. No duplicated statement, definition term, or group pair.
4. Nothing invented. If the OCR is too corrupted to read a sentence safely,
   leave it out. A smaller clean bank beats a bigger dirty one.
5. No page furniture: skip cover, preface, credits, page numbers, exercise
   blanks, and table-of-contents lines.

## Verify

```bash
python3 app/check_facts.py <code>     # must print "problems: 0"
```

Warnings (repeated group values, short facts, non-noun keys) are tolerated but
should be reduced — they cost questions.

## Volume target per chapter

| field     | per chapter |
|-----------|-------------|
| defs      | 8–20        |
| facts     | 25–60       |
| tf_false  | ≈ facts     |
| groups    | 2–5         |
| cq        | 2–4         |
| terms     | 6–12        |

Aim for the upper end on chapters with dense prose. Every fact also feeds a
fill item and usually an MCQ, so facts are the highest-value field.

## Style notes

* Bengali of the 2026 NCTB books: use `পানি` and `জল` as the book does, keep the
  book's spelling, and write numbers in Bengali digits.
* Definitions must be self-contained; a student who never read the page should
  still understand them.
* Statements should read like textbook sentences, not exam clues.
