#!/usr/bin/env python3
"""Build the Class 3 question bank for every NCTB subject.

Quality rules baked into this generator:

* one question per curated textbook fact, nothing invented;
* MCQ distractors are *chapter vocabulary* (real terms of the same lesson), so
  wrong options are plausible instead of filler;
* blanks absorb the Bengali case suffix ("পদার্থ" -> "——" + "ের"), so a fill
  item never produces broken text like "——ের";
* a true/false sentence may only be falsified by swapping the answer for
  another vocabulary term of the same chapter — never by gluing "না" on;
* every text field must be clean Bengali, so OCR noise can never ship.

    python3 app/gen_c3.py --report
    python3 app/gen_c3.py
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SEED_DIR = ROOT / "seed"
CLASSES_DIR = ROOT.parent / "classes"
BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_BN = str.maketrans("0123456789", BN_DIGITS)

SUBJECT_MODULES = [
    "facts_c3.sci",
    "facts_c3.ban",
    "facts_c3.eng",
    "facts_c3.math",
    "facts_c3.isl",
    "facts_c3.hin",
    "facts_c3.bud",
    "facts_c3.chr",
    "facts_c3.bws",
]

# Per-script question wording.  Bengali-medium books reuse the Bengali
# templates; the English book gets English stems so the paper reads naturally.
PHRASES = {
    "bn": {
        "def_q": "{d}—এটি কী?",
        "def_a": "{term} কী?",
        "fill_q": "শূন্যস্থানে সঠিক শব্দটি বেছে নাও: {blank}",
        "match_q": "বাম পাশের সাথে ডান পাশের সঠিক অংশ মিলাও: {category}",
        "fill_def": "{d}—এটি ——।",
        "def_mcq": "‘{t}’-এর সঠিক সংজ্ঞা কোনটি?",
        "pair_mcq": "‘{cat}’-এ ‘{l}’-এর সাথে কোনটি মেলে?",
        "match_def": "বাম পাশের শব্দকে ডান পাশের সংজ্ঞার সাথে মিলাও: {cat}",
        "cq_q": "উদ্দীপক পড়ে নিচের প্রশ্নগুলোর উত্তর দাও।",
        "true": "শুদ্ধ",
        "false": "অশুদ্ধ",
    },
    "en": {
        "def_q": "Which word means \"{d}\"?",
        "def_a": "What is {term}?",
        "fill_q": "Choose the correct word: {blank}",
        "match_q": "Match the left side with the correct right side: {category}",
        "fill_def": '"{d}" means ----.',
        "def_mcq": 'What is the correct meaning of "{t}"?',
        "pair_mcq": 'In "{cat}", which one matches "{l}"?',
        "match_def": 'Match each word on the left with its meaning on the right: {cat}',
        "cq_q": "Read the passage and answer the questions below.",
        "true": "True",
        "false": "False",
    },
}
PHRASES["math"] = PHRASES["bn"]

# U+0964/U+0965 are the danda/double danda that Bengali also uses, so legal.
BAD_CHARS = re.compile(r"[A-Za-z\u0600-\u06FF\u0900-\u0963\u0966-\u097F\u09E4]")
ALLOWED_PUNCT = set("।?!—‘’\"'(),%-–:;…০১২৩৪৫৬৭৮৯")

# Case endings that must travel with the answer, not stay glued to the blank.
SUFFIXES = ["দের", "য়ের", "ের", "টির", "টার", "টি", "টা", "কে", "ে", "য়", "র"]

VERB_TAIL = re.compile(
    r"(?:^|\s)(করে|হয়|থাকে|যায়|পায়|দেয়|খায়|জন্মায়|বলে|হলো|হল|নয়|দেখায়|"
    r"পারে|কাটে|ফেলে|টানে|ধরে|বাড়ে|বাঁচে|বেঁচে|কষ্ট|শোষণ করে)$"
)


def bn(n: int) -> str:
    return str(n).translate(_BN)


def tidy(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\u09e4", "।")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([।?!,;:])", r"\1", s)
    s = re.sub(r"([।?!])\1+", r"\1", s)
    return s


MATH_PUNCT = ALLOWED_PUNCT | set("+−-×÷*/=<>≤≥.")
EN_PUNCT = set(".,!?'\"()%-–—:;…/+=")


def ensure_danda(s: str, script: str = "bn") -> str:
    s = tidy(s)
    end = "." if script == "en" else "।"
    if s and not s.endswith(("।", "?", "!", ".")):
        s += end
    return s


def clean_text(s: str, script: str = "bn") -> bool:
    """Validate generated text for the script of its subject.

    ``bn`` keeps the strict Bengali-only filter that rejects OCR junk in the
    Bengali books.  ``en`` allows Latin letters, and ``math`` additionally
    allows arithmetic operators, because Class 3 English and Mathematics use
    them in their stems.
    """
    s = tidy(s)
    if not s:
        return False
    if script == "en":
        if re.search(r"[\u0600-\u06FF\u0900-\u097F]", s):
            return False
        if sum(1 for c in s if c.isascii() and c.isalpha()) < 2:
            return False
        return all(c == " " or (c.isascii() and c.isalnum()) or c in EN_PUNCT
                   for c in s)
    if script == "math":
        if re.search(r"[A-Za-z\u0600-\u06FF\u0900-\u0963\u0966-\u097F\u09E4]", s):
            return False
        if not any("\u0980" <= c <= "\u09ff" for c in s):
            return False
        return all(c == " " or "\u0980" <= c <= "\u09ff" or c in MATH_PUNCT
                   for c in s)
    if BAD_CHARS.search(s):
        return False
    if sum(1 for c in s if "\u0980" <= c <= "\u09ff") < 2:
        return False
    for c in s:
        if c == " " or "\u0980" <= c <= "\u09ff" or c in ALLOWED_PUNCT:
            continue
        return False
    return True


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(rf"[^\w\u0980-\u09FF]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def grams(s: str, n: int = 5) -> set:
    w = norm(s).split()
    if len(w) < n:
        return {tuple(w)} if w else set()
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class Deduper:
    """Global near-duplicate guard, per question type."""

    THRESHOLD = 0.70

    def __init__(self) -> None:
        self.exact: set[str] = set()
        self.by_type: dict[str, list[set]] = defaultdict(list)
        self.dropped = defaultdict(int)

    def accept(self, q: dict) -> bool:
        basis = q["stem"]
        if q["type"] == "cq":
            basis = q.get("stimulus", "") + " " + basis
        key = norm(basis)
        if not key:
            self.dropped["empty"] += 1
            return False
        if key in self.exact:
            self.dropped["exact"] += 1
            return False
        g = grams(basis)
        for other in self.by_type[q["type"]]:
            if jaccard(g, other) >= self.THRESHOLD:
                self.dropped["near"] += 1
                return False
        self.exact.add(key)
        self.by_type[q["type"]].append(g)
        return True


def noun_like(term: str) -> bool:
    t = tidy(term)
    if not t or len(t.split()) > 3:
        return False
    if VERB_TAIL.search(t):
        return False
    if t.startswith(("যে ", "যা ", "একটি ")):
        return False
    return True


def similar(a: str, b: str) -> bool:
    wa, wb = set(norm(a).split()), set(norm(b).split())
    if not wa or not wb:
        return True
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.5


def pick_distractors(answer: str, vocab: list[str], rnd: random.Random,
                     n: int = 3, avoid: str = "") -> list[str] | None:
    """Real chapter terms, similar in shape, clearly different in meaning."""
    a = norm(answer)
    avoid_n = norm(avoid)
    cand, seen = [], {a}
    for t in vocab:
        t = tidy(t)
        k = norm(t)
        if not k or k in seen:
            continue
        if not noun_like(t):
            continue
        if k in a or a in k:
            continue
        if avoid_n and k in avoid_n:
            continue
        if similar(t, answer):
            continue
        seen.add(k)
        cand.append(t)
    if len(cand) < n:
        return None
    rnd.shuffle(cand)
    cand.sort(key=lambda t: abs(len(t) - len(answer)))
    chosen = cand[:n]
    if len({norm(c) for c in chosen}) < n:
        return None
    return chosen


def falsifiable(statement: str, key: str, vocab: list[str]) -> bool:
    """Only swap a term that sits in the predicate, otherwise the result is
    ungrammatical ("... ও মাকড়সা করে")."""
    body = statement.rstrip("।?! ")
    i = body.find(key)
    if i < 0:
        return False
    # Prefix/suffix are preserved by the swap, and both terms come from one
    # curated class, so the result stays grammatical.  The only unsafe case is
    # a bare count noun replacing a gerund ("চলাফেরা করে" -> "মাকড়সা করে"),
    # which the class lists themselves prevent.
    after = body[i + len(key):].lstrip()
    if after.startswith(("একটি ", "একজন ", "একটা ")):
        return False              # "গুল্ম একটি বৃক্ষ" -> key is the copula subject
    return True


def blank_phrase(statement: str, key: str,
                 script: str = "bn") -> tuple[str, str] | None:
    """Replace `key` with a blank, taking its case suffix along."""
    st = ensure_danda(statement, script)
    i = st.find(key)
    if i < 0:
        return None
    if i > 0 and "\u0980" <= st[i - 1] <= "\u09ff":
        return None                      # match starts inside another word
    tail = st[i + len(key):]
    answer = key
    for suf in SUFFIXES:
        if tail.startswith(suf):
            answer = key + suf
            tail = tail[len(suf):]
            break
    if script == "en" and tail[:1].isascii() and tail[:1].isalpha():
        return None                      # "cat" inside "cats": avoid "——s"
    if tail[:1] and "\u0980" <= tail[0] <= "\u09ff" and not any(
            tail.startswith(s) for s in SUFFIXES):
        return None                      # key is glued to a different word
    blank = st[:i] + "——" + tail
    if len(blank.split()) < 3:
        return None
    return blank, answer


class Builder:
    def __init__(self, dedupe: Deduper, script: str = "bn") -> None:
        self.dedupe = dedupe
        self.script = script
        self.questions: list[dict] = []
        self.counters = defaultdict(int)
        self.rejected = defaultdict(int)

    def add(self, q: dict) -> None:
        fields = [q["stem"], q.get("answer_text", "")]
        fields += q.get("options", [])
        fields += [s["text"] for s in q.get("subquestions", [])]
        fields += q.get("left", []) + q.get("right", [])
        if q.get("stimulus"):
            fields.append(q["stimulus"])
        fields = [t for t in fields if t]
        if not all(clean_text(t, self.script) for t in fields):
            self.rejected["dirty_text"] += 1
            return
        if q["type"] == "mcq":
            opts = [norm(o) for o in q.get("options", [])]
            if len(opts) != 4 or len(set(opts)) != 4:
                self.rejected["bad_options"] += 1
                return
            if not (1 <= int(q.get("answer_index") or 0) <= 4):
                self.rejected["bad_answer"] += 1
                return
        if not self.dedupe.accept(q):
            return
        self.counters[q["type"]] += 1
        q["id"] = f"{q['id_prefix']}-{q['type']}-{self.counters[q['type']]:03d}"
        self.questions.append(q)


def base_question(code: str, ch: int, title: str, typ: str, stem: str,
                  subject: str, source: str, **extra) -> dict:
    q = {
        "id_prefix": f"c3{code}-c{ch}",
        "type": typ,
        "stem": tidy(stem),
        "marks": extra.pop("marks", 1),
        "bloom": extra.pop("bloom", "remember"),
        "difficulty": extra.pop("difficulty", 1),
        "class_name": "3",
        "subject": subject,
        "subject_code": code,
        "chapter_title": title,
        "chapter": str(ch),
        "source": source,
    }
    q.update(extra)
    return q


def build_chapter(b: Builder, code: str, subject: str, source: str,
                  ch: int, data: dict, book_vocab: list[str],
                  script: str = "bn") -> None:
    title = data["title"]
    rnd = random.Random(f"{code}-{ch}")
    ph = PHRASES.get(script, PHRASES["bn"])

    def danda(s: str) -> str:
        return ensure_danda(s, script)

    defs = data.get("defs", [])
    facts = data.get("facts", [])
    qa = data.get("qa", [])
    groups = data.get("groups", [])
    cqs = data.get("cq", [])

    # Only curated nouns may become options or replacement terms.
    vocab = list(dict.fromkeys(
        list(data.get("terms", [])) + [t for t, _ in defs]
    ))
    pool = list(dict.fromkeys(vocab + book_vocab))

    # Co-hyponym classes: a false statement may only swap a term for another
    # term of the *same* class (plant types, senses, seasons ...), which keeps
    # wrong options plausible instead of absurd.
    classes: list[list[str]] = [list(c) for c in data.get("classes", [])]
    for _cat, pairs in groups:
        classes.append([tidy(a) for a, _ in pairs])
        classes.append([tidy(b) for _, b in pairs])
    class_of: dict[str, list[str]] = {}
    for cls in classes:
        cls = [t for t in dict.fromkeys(cls) if noun_like(t)]
        if len(cls) < 2:
            continue
        for t in cls:
            class_of.setdefault(t, [])
            for o in cls:
                if o != t and o not in class_of[t]:
                    class_of[t].append(o)

    # ---- definition -> term MCQ + জ্ঞানমূলক -----------------------------
    for term, definition in defs:
        if not noun_like(term):
            continue
        d = tidy(definition).rstrip("।")
        opts = (pick_distractors(term, class_of.get(term, []) + vocab, rnd, avoid=d)
                or pick_distractors(term, vocab, rnd, avoid=d)
                or pick_distractors(term, pool, rnd, avoid=d))
        if opts:
            options = opts + [tidy(term)]
            rnd.shuffle(options)
            b.add(base_question(
                code, ch, title, "mcq", ph["def_q"].format(d=d), subject, source,
                options=options,
                answer_index=options.index(tidy(term)) + 1,
                answer_text=tidy(term), difficulty=2,
            ))
        b.add(base_question(
            code, ch, title, "wrq_k", ph["def_a"].format(term=tidy(term)),
            subject, source,
            answer_text=danda(definition),
            explanation=danda(definition),
        ))

    # A true/false section where nearly every item is true teaches nothing, so
    # when curated false statements exist the true ones are sampled down to
    # match them.  Mechanical term swapping is not used: it silently turns true
    # statements into "false" ones ("লেবুর শরবত স্বাস্থ্যকর পানীয়") and cannot be
    # verified without a human reading every item.
    tf_false = data.get("tf_false", [])
    keep_true = None
    if tf_false and facts:
        want = max(1, round(len(tf_false) * 1.05))
        idx = list(range(len(facts)))
        rnd.shuffle(idx)
        keep_true = {facts[i][0] for i in sorted(idx[:want])}

    # ---- facts -> fill / MCQ / TF ---------------------------------------
    for statement, key in facts:
        pair = blank_phrase(statement, key, script)
        if not pair:
            continue
        blank, answer = pair
        st = danda(statement)

        b.add(base_question(
            code, ch, title, "fill", blank, subject, source,
            answer_text=answer,
        ))

        opts = (pick_distractors(answer, class_of.get(key, []) + vocab, rnd)
                or pick_distractors(answer, vocab, rnd)
                or pick_distractors(answer, pool, rnd))
        if opts:
            options = opts + [answer]
            rnd.shuffle(options)
            b.add(base_question(
                code, ch, title, "mcq",
                ph["fill_q"].format(blank=blank), subject, source,
                options=options,
                answer_index=options.index(answer) + 1,
                answer_text=answer,
            ))

        if keep_true is None or statement in keep_true:
            b.add(base_question(
                code, ch, title, "tf", st, subject, source,
                answer_bool=True, answer_text=ph["true"],
            ))

        # fallback for fact bases without curated false statements: swap the
        # key for a same-class term, which stays grammatical
        if keep_true is None:
            mates = class_of.get(key, [])
            if mates and falsifiable(st, key, vocab):
                sibs = pick_distractors(key, mates, rnd, n=1,
                                        avoid=st.replace(key, " "))
                if sibs:
                    b.add(base_question(
                        code, ch, title, "tf", st.replace(key, sibs[0], 1),
                        subject, source, answer_bool=False,
                        answer_text=ph["false"], difficulty=2,
                    ))

    # ---- hand-authored false statements ----------------------------------
    # Curated items are the only reliable way to keep a 50/50 true/false
    # balance: a mechanical swap cannot falsify a whole-clause fact.
    for false_stmt, correction in data.get("tf_false", []):
        b.add(base_question(
            code, ch, title, "tf", danda(false_stmt), subject, source,
            answer_bool=False, answer_text=ph["false"],
            explanation=danda(correction) if correction else "",
            difficulty=2,
        ))

    # ---- textbook short answers ------------------------------------------
    for question, answer in qa:
        b.add(base_question(
            code, ch, title, "wrq_k", question, subject, source,
            answer_text=danda(answer),
            explanation=danda(answer),
        ))

    # ---- matching --------------------------------------------------------
    for category, pairs in groups:
        left, rights = [], []
        seen_l, seen_r = set(), set()
        for a, c in pairs:
            a, c = tidy(a), tidy(c)
            if not a or not c or norm(a) in seen_l or norm(c) in seen_r:
                continue
            seen_l.add(norm(a))
            seen_r.add(norm(c))
            left.append(a)
            rights.append(c)
        left, rights = left[:5], rights[:5]
        if len(left) < 3:
            continue
        order = list(range(len(rights)))
        rnd.shuffle(order)
        shuffled = [rights[i] for i in order]
        answer_key = [shuffled.index(r) for r in rights]
        b.add(base_question(
            code, ch, title, "match",
            ph["match_q"].format(category=category), subject, source,
            left=left, right=shuffled, answer_key=answer_key,
            marks=len(left), bloom="understand", difficulty=2,
        ))

    # ---- creative questions ----------------------------------------------
    for stimulus, subs, answer in cqs:
        b.add(base_question(
            code, ch, title, "cq", ph["cq_q"], subject, source,
            stimulus=tidy(stimulus),
            subquestions=[{"label": l, "text": tidy(t), "marks": m} for l, t, m in subs],
            answer_text=danda(answer), marks=10, bloom="apply", difficulty=3,
        ))

    # ---- definition -> fill-in-the-blank (one extra item per definition) ---
    for term, definition in defs:
        d = tidy(definition).rstrip("।")
        stem = ensure_danda(ph["fill_def"].format(d=d), script)
        b.add(base_question(
            code, ch, title, "fill", stem, subject, source,
            answer_text=tidy(term), marks=1, bloom="remember", difficulty=1,
        ))

    # ---- definition -> term MCQ: which definition fits the term? ----------
    defs_clean = [(tidy(t), tidy(defn).rstrip("।")) for t, defn in defs]
    defs_uniq = list(dict.fromkeys(defs_clean))
    if len(defs_uniq) >= 4:
        for term, d in defs_uniq:
            others = [dd for tt, dd in defs_uniq if tt != term and norm(dd) != norm(d)]
            options = [d] + others[:3]
            if len(options) != 4 or len({norm(o) for o in options}) != 4:
                continue
            rnd.shuffle(options)
            b.add(base_question(
                code, ch, title, "mcq",
                ph["def_mcq"].format(t=tidy(term)), subject, source,
                options=options,
                answer_index=options.index(d) + 1,
                answer_text=d, difficulty=2, bloom="understand",
            ))

    # ---- groups -> MCQ: which right side matches the left side? -----------
    for category, pairs in groups:
        pairs2 = [(tidy(a), tidy(c)) for a, c in pairs]
        rights = list(dict.fromkeys(c for _, c in pairs2))
        if len(rights) < 4:
            continue
        for left, right in pairs2:
            # skip trivial identity matches where the answer is literally the
            # left item (answer already visible in the stem)
            if norm(left) == norm(right):
                continue
            distractors = [r for r in rights
                           if norm(r) != norm(right)
                           and norm(right) not in norm(r)     # distractor ⊉ answer
                           and norm(r) not in norm(right)]    # answer ⊉ distractor
            if len(distractors) < 3:
                continue                                     # not enough good options
            distractors = distractors[:3]
            options = [right] + distractors
            rnd.shuffle(options)
            b.add(base_question(
                code, ch, title, "mcq",
                ph["pair_mcq"].format(cat=tidy(category), l=tidy(left)), subject, source,
                options=options,
                answer_index=options.index(right) + 1,
                answer_text=right, difficulty=1, bloom="remember",
            ))

    # ---- defs -> auto match sets (term <-> definition) -------------------
    set_label = "সেট" if script != "en" else "set"
    for si in range(0, len(defs_uniq), 5):
        chunk = defs_uniq[si:si + 5]
        if len(chunk) < 4:
            continue
        lefts = [t for t, _ in chunk]
        rights = [d for _, d in chunk]
        if len({norm(r) for r in rights}) != len(rights):
            continue
        order = list(range(len(rights)))
        rnd.shuffle(order)
        shuffled = [rights[i] for i in order]
        answer_key = [shuffled.index(r) for r in rights]
        # English uses ASCII digits; Bengali/Math use Bengali digits.
        set_num = str(si // 5 + 1) if script == "en" else bn(si // 5 + 1)
        b.add(base_question(
            code, ch, title, "match",
            ph["match_def"].format(cat=f"{title} {set_label} {set_num}"), subject, source,
            left=lefts, right=shuffled, answer_key=answer_key,
            marks=len(lefts), bloom="understand", difficulty=2,
        ))


def load_subjects() -> list[dict]:
    out = []
    for mod_name in SUBJECT_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue
        except Exception as exc:            # broken module must not stop the run
            print(f"warning: skipping {mod_name}: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        subject = getattr(mod, "SUBJECT", None)
        if not isinstance(subject, dict) or not subject.get("chapters"):
            print(f"warning: skipping {mod_name}: no SUBJECT['chapters']",
                  file=sys.stderr)
            continue
        # Optional companion module with hand-authored false statements, so a
        # large fact base can be extended without touching its source file.
        code = subject.get("code")
        if code:
            try:
                extra = importlib.import_module(f"facts_c3.{code}_tf")
            except ModuleNotFoundError:
                extra = None
            except Exception as exc:
                print(f"warning: ignoring facts_c3.{code}_tf: "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
                extra = None
            if extra is not None:
                for ch, items in getattr(extra, "TF_FALSE", {}).items():
                    node = subject["chapters"].get(int(ch))
                    if node is None:
                        continue
                    node["tf_false"] = list(node.get("tf_false", [])) + list(items)
        out.append(subject)
    return out


def build_subject(subject_data: dict, dedupe: Deduper) -> tuple[list[dict], dict]:
    script = subject_data.get("script", "bn")
    b = Builder(dedupe, script)
    chapters = subject_data["chapters"]
    book_vocab: list[str] = []
    for ch in chapters.values():
        book_vocab += list(ch.get("terms", []))
        book_vocab += [t for t, _ in ch.get("defs", [])]
    book_vocab = list(dict.fromkeys(tidy(t) for t in book_vocab if tidy(t)))

    for ch in sorted(chapters):
        build_chapter(b, subject_data["code"], subject_data["subject"],
                      subject_data["source"], int(ch), chapters[ch], book_vocab,
                      script)
    report = {
        "code": subject_data["code"],
        "subject": subject_data["subject"],
        "total": len(b.questions),
        "by_type": dict(b.counters),
        "rejected": dict(b.rejected),
        "chapters": len(chapters),
    }
    return b.questions, report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    SEED_DIR.mkdir(exist_ok=True)
    CLASSES_DIR.mkdir(exist_ok=True)

    dedupe = Deduper()
    chapter_map: dict[str, str] = {}
    subject_names: list[str] = []
    reports, combined = [], []

    subjects = load_subjects()
    if not subjects:
        print("no facts_c3 modules found")
        return 1

    for subj in subjects:
        qs, rep = build_subject(subj, dedupe)
        reports.append(rep)
        if not qs:
            print(f"skip {subj['subject']}: no questions")
            continue
        subject_names.append(f"{subj['subject']} ({subj['book']})")
        for ch, chdata in subj["chapters"].items():
            chapter_map.setdefault(f"{subj['code']}:{ch}", chdata["title"])
        payload = {
            "meta": {
                "class_name": "3",
                "subject": subj["subject"],
                "book": subj["book"],
                "source": subj["source"],
                "chapters": len(subj["chapters"]),
                "chapter_map": {str(c): d["title"]
                                for c, d in sorted(subj["chapters"].items())},
                "bank_version": 3,
                "generated_by": "app/gen_c3.py",
            },
            "questions": qs,
        }
        (SEED_DIR / f"class3_{subj['code']}_all.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        combined += qs

    for rep in reports:
        by = rep["by_type"]
        print(f"{rep['subject']:22s} ch={rep['chapters']:2d} total={rep['total']:5d} "
              f"mcq={by.get('mcq', 0):4d} fill={by.get('fill', 0):4d} "
              f"tf={by.get('tf', 0):4d} match={by.get('match', 0):3d} "
              f"wrq_k={by.get('wrq_k', 0):4d} cq={by.get('cq', 0):3d}  "
              f"rejected={rep['rejected']}")
    print(f"TOTAL {sum(r['total'] for r in reports)} questions, "
          f"dropped={dict(dedupe.dropped)}")

    if args.report:
        return 0

    payload = {
        "meta": {
            "class_name": "3",
            "subjects": subject_names,
            "source": "NCTB তৃতীয় শ্রেণি পাঠ্যবই (২০২৬ শিক্ষাবর্ষ)",
            "chapters": len(chapter_map),
            "chapter_map": chapter_map,
            "bank_version": 3,
            "generated_by": "app/gen_c3.py",
        },
        "questions": combined,
    }
    out = CLASSES_DIR / "class-3.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024 / 1024:.2f} MB, "
          f"{len(combined)} questions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
