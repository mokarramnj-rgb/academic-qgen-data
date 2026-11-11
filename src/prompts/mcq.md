You are writing exam questions for the Bangladeshi national curriculum.

Class: {class_name}
Subject: {subject}
Chapter: {chapter}
Number of items: {n}
Difficulty mix: {bloom_mix}

STYLE TARGET (mined from a separate, licensed question corpus):
{style}

REFERENCE (the only permitted source of facts):
---
{reference}
---

Write {n} multiple-choice questions in **Bangla**, following these rules:

1. Match the archetype mix and stem length above, but never copy wording from
   the style corpus — it is only a shape reference.
2. Each item has exactly 4 options, only one correct.
3. Distractors must be plausible: common misconceptions, near-misses, or
   reversed relationships. No joke options, no "all of the above".
4. The stem must be answerable from the reference alone. Do not invent facts,
   dates, names, or numbers that are not in the reference.
5. Do not copy sentences from the reference; paraphrase.
6. Vary the position of the correct answer.
7. Add a one-to-two sentence explanation that cites the relevant fact.
8. Tag each item with a Bloom level: remember | understand | apply | analyze.

Return JSON only, as an array:

[
  {{
    "stem": "প্রশ্ন...",
    "options": ["...", "...", "...", "..."],
    "answer_index": 1,
    "explanation": "...",
    "bloom": "understand",
    "difficulty": 0.45,
    "source_span": "short quote or page reference from the reference"
  }}
]
