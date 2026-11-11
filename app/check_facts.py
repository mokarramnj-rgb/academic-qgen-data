#!/usr/bin/env python3
"""Validate one facts_c3 subject module before it is fed to the generator.

    python3 app/check_facts.py            # check every module
    python3 app/check_facts.py ban isl    # check selected subjects

Every rule here exists because it produced a bad question once:

* non-Bengali characters came from OCR and must never ship;
* a fact whose key is not inside its statement yields an unanswerable item;
* a key that is a verb phrase ("চলাফেরা করে") makes a nonsense MCQ;
* duplicated right-hand sides make a matching item ambiguous;
* a creative question without ক/খ/গ/ঘ labels breaks the paper layout.
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gen_c3 as g  # noqa: E402

CODES = ["sci", "ban", "eng", "math", "isl", "hin", "bud", "chr", "bws"]
LABELS = ["ক", "খ", "গ", "ঘ"]


def bad_text(s: str, script: str = "bn", min_letters: int = 2) -> str | None:
    if not isinstance(s, str):
        return "not a string"
    if not s.strip():
        return "empty"
    if script != "bn":
        # English / Mathematics modules have their own charter; reuse the
        # generator's validator so the two checks can never disagree.
        if not g.clean_text(s, script):
            return f"invalid characters for script {script!r}"
        return None
    if g.BAD_CHARS.search(s):
        return "non-Bengali characters"
    if sum(1 for c in s if "\u0980" <= c <= "\u09ff") < min_letters:
        return "too few Bengali letters"
    for c in s:
        if c == " " or "\u0980" <= c <= "\u09ff" or c in g.ALLOWED_PUNCT:
            continue
        return f"disallowed character {c!r}"
    return None


# Findings the generator already neutralises on its own: worth showing, but
# they must not block a fact base from being built.
SECTIONS_LOG: list[str] = []


def check_subject(code: str) -> list[str]:
    errs: list[str] = []
    try:
        mod = importlib.import_module(f"facts_c3.{code}")
    except ModuleNotFoundError:
        return [f"{code}: module missing"]
    subj = mod.SUBJECT
    script = subj.get("script", "bn")

    def bt(s: str, min_letters: int = 2) -> str | None:
        return bad_text(s, script, min_letters)

    for k in ("code", "subject", "book", "source", "chapters"):
        if k not in subj:
            errs.append(f"{code}: SUBJECT missing {k!r}")
    if subj.get("code") != code:
        errs.append(f"{code}: SUBJECT['code'] is {subj.get('code')!r}")

    chapters = subj.get("chapters", {})
    try:
        extra = importlib.import_module(f"facts_c3.{code}_tf")
    except ModuleNotFoundError:
        extra = None
    if extra is not None:
        for ch, items in getattr(extra, "TF_FALSE", {}).items():
            if int(ch) not in chapters:
                errs.append(f"{code}_tf: chapter {ch} does not exist")
                continue
            chapters[int(ch)]["tf_false"] = list(chapters[int(ch)].get("tf_false", [])) + list(items)

    if len(chapters) < 3:
        errs.append(f"{code}: only {len(chapters)} chapters")

    for ch, data in chapters.items():
        tag = f"{code}/ch{ch}"
        for k in ("title", "defs", "facts"):
            if k not in data:
                errs.append(f"{tag}: missing {k!r}")
        if not data.get("title"):
            errs.append(f"{tag}: empty title")

        terms = data.get("terms", [])
        defs = data.get("defs", [])
        facts = data.get("facts", [])

        if len(defs) < 6:
            errs.append(f"{tag}: only {len(defs)} defs")
        if len(facts) < 10:
            errs.append(f"{tag}: only {len(facts)} facts")

        seen_terms: set[str] = set()
        for item in defs:
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                errs.append(f"{tag}: def is not (term, definition): {item!r}")
                continue
            term, definition = item
            for piece, what in ((term, "term"), (definition, "definition")):
                e = bt(piece)
                if e:
                    errs.append(f"{tag}: def {what} {e}: {piece!r}")
            key = g.norm(term)
            if key in seen_terms:
                errs.append(f"{tag}: duplicate def {term!r}")
            seen_terms.add(key)
            if not g.noun_like(term):
                errs.append(f"{tag}: def term not noun-like: {term!r}")
            d = g.tidy(definition).rstrip("।")
            if len(d) < 8:
                SECTIONS_LOG.append(f"{tag}: def too short: {term!r} -> {definition!r}")
            elif len(d) > 180:
                errs.append(f"{tag}: def too long: {term!r}")

        seen_facts: set[str] = set()
        for item in facts:
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                errs.append(f"{tag}: fact is not (statement, key): {item!r}")
                continue
            stmt, key = item
            e = bt(stmt)
            if e:
                errs.append(f"{tag}: fact {e}: {stmt!r}")
                continue
            e = bt(key)
            if e:
                errs.append(f"{tag}: fact key {e}: {key!r}")
                continue
            if key.strip() not in stmt:
                errs.append(f"{tag}: key not in statement: {key!r} / {stmt!r}")
                continue
            k = g.norm(stmt)
            if k in seen_facts:
                errs.append(f"{tag}: duplicate fact {stmt!r}")
            seen_facts.add(k)
            if not g.noun_like(key):
                SECTIONS_LOG.append(f"{tag}: key not noun-like: {key!r} in {stmt!r}")
            if len(stmt) < 12:
                SECTIONS_LOG.append(f"{tag}: fact too short: {stmt!r}")
            elif len(stmt) > 220:
                errs.append(f"{tag}: fact too long: {stmt!r}")
            hits = [m.start() for m in re.finditer(re.escape(key), stmt)]
            whole = [h for h in hits
                     if (h == 0 or not ("\u0980" <= stmt[h - 1] <= "\u09ff"))
                     and (h + len(key) >= len(stmt)
                          or not ("\u0980" <= stmt[h + len(key)] <= "\u09ff"))]
            if len(whole) > 1:
                errs.append(f"{tag}: key appears twice, blank is ambiguous: {stmt!r}")

        for item in data.get("tf_false", []):
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                errs.append(f"{tag}: tf_false is not (statement, correction)")
                continue
            stmt, fix = item
            e = bt(stmt)
            if e:
                errs.append(f"{tag}: tf_false {e}: {stmt!r}")
            if fix:
                e = bt(fix)
                if e:
                    errs.append(f"{tag}: tf_false correction {e}: {fix!r}")
            if g.norm(stmt) in seen_facts:
                errs.append(f"{tag}: tf_false duplicates a true fact: {stmt!r}")

        for item in data.get("groups", []):
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                errs.append(f"{tag}: group is not (category, pairs)")
                continue
            category, pairs = item
            e = bt(category)
            if e:
                errs.append(f"{tag}: group category {e}: {category!r}")
            if len(pairs) < 3:
                errs.append(f"{tag}: group {category!r} has only {len(pairs)} pairs")
            rights, lefts = set(), set()
            for pair in pairs[:5]:
                if len(pair) != 2:
                    errs.append(f"{tag}: group {category!r} bad pair {pair!r}")
                    continue
                a, c = pair
                for piece in (a, c):
                    e = bt(piece)
                    if e:
                        errs.append(f"{tag}: group {e}: {piece!r}")
                if g.norm(c) in rights:
                    SECTIONS_LOG.append(f"{tag}: group {category!r} repeated right {c!r}")
                if g.norm(a) in lefts:
                    SECTIONS_LOG.append(f"{tag}: group {category!r} repeated left {a!r}")
                rights.add(g.norm(c))
                lefts.add(g.norm(a))

        for item in data.get("cq", []):
            if len(item) != 3:
                errs.append(f"{tag}: cq is not (stimulus, subquestions, answer)")
                continue
            stim, subs, answer = item
            e = bt(stim)
            if e:
                errs.append(f"{tag}: cq stimulus {e}: {stim!r}")
            if len(stim) < 30:
                errs.append(f"{tag}: cq stimulus too short: {stim!r}")
            if not (3 <= len(subs) <= 4):
                errs.append(f"{tag}: cq has {len(subs)} subquestions")
            for i, sub in enumerate(subs):
                if len(sub) != 3:
                    errs.append(f"{tag}: cq subquestion malformed: {sub!r}")
                    continue
                label, text, marks = sub
                want = LABELS[i] if script != "en" else "abcd"[i]
                if label != want:
                    errs.append(f"{tag}: cq label {label!r} should be {want!r}")
                e = bt(text)
                if e:
                    errs.append(f"{tag}: cq subquestion {e}: {text!r}")
                if marks not in (1, 2, 3, 4):
                    errs.append(f"{tag}: cq marks {marks!r} invalid")
            e = bt(answer)
            if e:
                errs.append(f"{tag}: cq answer {e}: {answer!r}")

        for t in terms:
            e = bt(t)
            if e:
                errs.append(f"{tag}: term {e}: {t!r}")
            elif not g.noun_like(t):
                errs.append(f"{tag}: term not noun-like: {t!r}")

        for cls in data.get("classes", []):
            if len(cls) < 2:
                errs.append(f"{tag}: class too small: {cls!r}")
            for t in cls:
                e = bt(t)
                if e:
                    errs.append(f"{tag}: class member {e}: {t!r}")
                elif not g.noun_like(t):
                    errs.append(f"{tag}: class member not noun-like: {t!r}")
    return errs


def main(argv: list[str]) -> int:
    codes = argv or CODES
    total = 0
    warn = 0
    for code in codes:
        try:
            errs = check_subject(code)
        except Exception as exc:  # noqa: BLE001
            print(f"{code}: CRASH {type(exc).__name__}: {exc}")
            total += 1
            continue
        warn += len(SECTIONS_LOG)
        if SECTIONS_LOG:
            print(f"{code}: {len(SECTIONS_LOG)} warnings")
            for w in SECTIONS_LOG[:15]:
                print("   ~", w)
            if len(SECTIONS_LOG) > 15:
                print(f"    ... and {len(SECTIONS_LOG) - 15} more")
            SECTIONS_LOG.clear()
        if not errs:
            mod = importlib.import_module(f"facts_c3.{code}")
            ch = mod.SUBJECT["chapters"]
            print(f"{code}: OK  chapters={len(ch)} defs={sum(len(c.get('defs', [])) for c in ch.values())} "
                  f"facts={sum(len(c.get('facts', [])) for c in ch.values())} "
                  f"tf_false={sum(len(c.get('tf_false', [])) for c in ch.values())} "
                  f"cq={sum(len(c.get('cq', [])) for c in ch.values())}")
            continue
        total += len(errs)
        print(f"{code}: {len(errs)} problems")
        for e in errs[:60]:
            print("   ", e)
        if len(errs) > 60:
            print(f"    ... and {len(errs) - 60} more")
    print(f"\ntotal problems: {total}  warnings: {warn}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
