"""Generate validated MCQ items from a reference passage.

Works with any OpenAI-compatible chat endpoint:

    OPENAI_BASE_URL=https://opencode.ai/inference/openai/v1
    OPENAI_API_KEY=...            # or OPENCODE_API_KEY
    MODEL=deepseek-v4.1-flash-free

Local example:
    OPENAI_BASE_URL=http://127.0.0.1:11434/v1 OPENAI_API_KEY=ollama MODEL=qwen2.5:7b
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PROMPT_PATH = Path(__file__).with_name("prompts") / "mcq.md"


# ---------------------------------------------------------------- model call

def chat(messages: list[dict], temperature: float = 0.3,
         max_tokens: int = 3000) -> str:
    base = os.environ.get("OPENAI_BASE_URL", "https://opencode.ai/inference/openai/v1").rstrip("/")
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENCODE_API_KEY", "")
    model = os.environ.get("MODEL", "deepseek-v4.1-flash-free")

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def parse_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = min((i for i in (text.find("["), text.find("{")) if i != -1), default=-1)
    if start == -1:
        raise ValueError("model returned no JSON")
    end = max(text.rfind("]"), text.rfind("}"))
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------- validation

def fingerprint(stem: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", stem).strip().lower().encode()).hexdigest()


def word_ngrams(text: str, n: int = 5) -> set[tuple[str, ...]]:
    """Word n-grams. Bengali stems legitimately reuse 2-4 word phrases, so a
    word-level window is a much better copy detector than char n-grams."""
    words = re.sub(r"[^\w\u0980-\u09FF]+", " ", text).split()
    return {tuple(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def verbatim_ratio(stem: str, reference: str) -> float:
    grams = word_ngrams(stem)
    if not grams:
        return 0.0
    ref = word_ngrams(reference)
    return len(grams & ref) / len(grams)


def validate(item: dict, reference: str) -> list[str]:
    errors: list[str] = []
    stem = str(item.get("stem", "")).strip()
    options = item.get("options")
    answer = item.get("answer_index")

    if len(stem) < 10:
        errors.append("stem too short")
    if not isinstance(options, list) or len(options) != 4:
        errors.append("need exactly 4 options")
    elif len({o.strip() for o in options}) != 4:
        errors.append("options are not unique")
    if answer not in (1, 2, 3, 4):
        errors.append("answer_index must be 1..4")
    if not str(item.get("explanation", "")).strip():
        errors.append("missing explanation")
    if verbatim_ratio(stem, reference) > 0.5:
        errors.append("stem copies the reference verbatim")
    return errors


# ---------------------------------------------------------------- pipeline

def build_prompt(reference: str, class_name: str, subject: str,
                 chapter: str, n: int, bloom_mix: str,
                 style: dict | None = None) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(
        reference=reference.strip(),
        class_name=class_name,
        subject=subject,
        chapter=chapter,
        n=n,
        bloom_mix=bloom_mix,
        style=format_style(style),
    )


def format_style(profile: dict | None) -> str:
    """Compact, model-readable summary of the style corpus."""
    if not profile:
        return "No style profile supplied; use a balanced national-curriculum style."
    c = profile.get("corpus", {})
    stem = profile.get("stem_words", {})
    opt = profile.get("option_words", {})
    arche = profile.get("archetypes", [])[:6]
    bloom = profile.get("bloom_proxy", {})
    pos = profile.get("answer_position_share", {})
    lines = [
        f"- Items observed: {c.get('n', '?')} (answer coverage {c.get('answer_coverage', '?')})",
        f"- Stem length: mean {stem.get('mean', '?')} words, p90 {stem.get('p90', '?')}",
        f"- Option length: mean {opt.get('mean', '?')} words",
        "- Archetype mix: " + ", ".join(f"{a['id']} {int(a['share'] * 100)}%" for a in arche),
        "- Bloom mix: " + ", ".join(f"{k} {int(v * 100)}%" for k, v in bloom.items()),
        "- Answer position: " + ", ".join(f"{k} {int(v * 100)}%" for k, v in pos.items()),
    ]
    return "\n".join(lines)


def generate(reference: str, class_name: str, subject: str, chapter: str,
             n: int, bloom_mix: str = "1-2 recall, 2-3 understanding, 1 application",
             style: dict | None = None) -> list[dict]:
    prompt = build_prompt(reference, class_name, subject, chapter, n, bloom_mix, style)
    raw = chat([
        {"role": "system", "content": "You are an exam item writer. Output JSON only."},
        {"role": "user", "content": prompt},
    ])
    data = parse_json(raw)
    return data if isinstance(data, list) else data.get("items", [])


def verify(item: dict) -> bool:
    """Second pass: can the model answer its own item without the key?"""
    options = "\n".join(f"{i}. {o}" for i, o in enumerate(item["options"], 1))
    prompt = (
        "Answer this multiple-choice question. Reply with JSON "
        '{"answer_index": <1-4>} only.\n\n'
        f"{item['stem']}\n\n{options}"
    )
    try:
        out = parse_json(chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=50))
        return out.get("answer_index") == item["answer_index"]
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate MCQs from a reference text.")
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--class", dest="class_name", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--style", type=Path, help="style_profile.json mined from a corpus")
    ap.add_argument("--verify", action="store_true", help="second-pass answer check")
    args = ap.parse_args(argv)

    reference = args.ref.read_text(encoding="utf-8")
    style = json.loads(args.style.read_text(encoding="utf-8")) if args.style else None
    items = generate(reference, args.class_name, args.subject, args.chapter, args.n,
                     style=style)

    kept, rejected, seen = [], [], set()
    for item in items:
        errors = validate(item, reference)
        fp = fingerprint(str(item.get("stem", "")))
        if fp in seen:
            errors.append("duplicate")
        seen.add(fp)
        if args.verify and not errors and not verify(item):
            errors.append("second-pass answer mismatch")
        item["fingerprint"] = fp
        item["node_id"] = f"{args.class_name}/{args.subject}/{args.chapter}"
        item["status"] = "draft"
        (rejected if errors else kept).append({**item, "errors": errors} if errors else item)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for item in kept:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"generated {len(items)}  kept {len(kept)}  rejected {len(rejected)}")
    for bad in rejected:
        print("  reject:", bad["errors"], "|", str(bad.get("stem", ""))[:60])
    return 0


if __name__ == "__main__":
    sys.exit(main())
