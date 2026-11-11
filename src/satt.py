"""Satt Academy question-list parser.

Design rules:
  * Parsing a saved HTML file never touches the network.
  * URL mode respects robots.txt and never fetches a disallowed path.
  * No third-party dependencies.

Usage:
    python -m src.satt --html data/raw/class8.html --out data/class8_sample.jsonl
    python -m src.satt --url https://sattacademy.com/... --class 8 --out out.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import html as htmllib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, asdict
from pathlib import Path

UA = "academic-qgen/0.1 (research; contact: local-user)"
DELAY_SECONDS = 2.0

QUESTION_SPAN = re.compile(r'class="question-span')
OPTION_RE = re.compile(r'option-(\d)-text[^>]*>(.*?)</div>', re.S)
ANSWER_RE = re.compile(r'name="answer"\s+value="(\d+)"')
QID_RE = re.compile(r'option-\d-text"\s+data-id="(\d+)"')
URL_RE = re.compile(r'href="\s*(https://sattacademy\.com/mcq/[^"]+)"')
TAG_RE = re.compile(r'href="[^"]*/all-mcq/([^"]+)"')


def clean(fragment: str) -> str:
    """Strip tags, decode entities, collapse whitespace, keep line breaks."""
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = htmllib.unescape(fragment)
    fragment = re.sub(r"[ \t\u00a0]+", " ", fragment)
    return re.sub(r"\n\s*\n+", "\n", fragment).strip()


def fingerprint(stem: str) -> str:
    norm = re.sub(r"\s+", " ", stem).strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


@dataclass
class Question:
    id: str
    source: str
    url: str | None
    class_name: str | None
    stem: str
    options: list[str]
    answer_index: int | None       # 1-based; None when the page has no answer
    answer_text: str | None
    tags: list[str]
    answer_status: str             # "ok" | "missing"
    fingerprint: str

    def to_json(self) -> dict:
        return asdict(self)


def parse_questions(page_html: str, class_name: str | None = None,
                    source: str = "sattacademy.com") -> list[Question]:
    starts = [m.start() for m in QUESTION_SPAN.finditer(page_html)]
    questions: list[Question] = []

    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else start + 40_000
        chunk = page_html[start:end]

        tag_end = chunk.find(">")
        stem_end = chunk.find("</span>", tag_end)
        if tag_end == -1 or stem_end == -1:
            continue
        stem = clean(chunk[tag_end + 1:stem_end])
        if not stem:
            continue

        options: dict[int, str] = {}
        for n, raw in OPTION_RE.findall(chunk):
            text = clean(raw)
            if text:
                options[int(n)] = text
        if len(options) != 4:
            continue

        answer_match = ANSWER_RE.search(chunk)
        answer_index = int(answer_match.group(1)) if answer_match else 0
        if answer_index not in (1, 2, 3, 4):
            answer_index = None

        qid_match = QID_RE.search(chunk)
        qid = qid_match.group(1) if qid_match else fingerprint(stem)[:12]

        before = page_html[max(0, start - 4_000):start]
        urls = URL_RE.findall(before)
        url = urls[-1].strip() if urls else None

        tags = sorted({urllib.parse.unquote(t) for t in TAG_RE.findall(chunk)})

        questions.append(Question(
            id=qid,
            source=source,
            url=url,
            class_name=class_name,
            stem=stem,
            options=[options[n] for n in sorted(options)],
            answer_index=answer_index,
            answer_text=options[answer_index] if answer_index else None,
            tags=tags,
            answer_status="ok" if answer_index else "missing",
            fingerprint=fingerprint(stem),
        ))

    return questions


def robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    parts = urllib.parse.urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    req = urllib.request.Request(robots_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rp.parse(resp.read().decode("utf-8", "ignore").splitlines())
    return rp


def fetch(url: str, rp: urllib.robotparser.RobotFileParser) -> str:
    if not rp.can_fetch(UA, url):
        raise PermissionError(
            f"robots.txt disallows {url}. Refusing to fetch. "
            "Ask the site owner for permission or use a licensed dataset."
        )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "ignore")


def write_jsonl(questions: list[Question], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for q in questions:
            fh.write(json.dumps(q.to_json(), ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse Satt Academy question pages.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--html", type=Path, help="saved HTML file (offline)")
    src.add_argument("--url", help="fetch one allowed URL (robots-checked)")
    ap.add_argument("--class", dest="class_name", help="class label, e.g. 8")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    if args.html:
        page = args.html.read_text(encoding="utf-8", errors="ignore")
    else:
        rp = robots_for(args.url)
        time.sleep(DELAY_SECONDS)
        page = fetch(args.url, rp)

    questions = parse_questions(page, class_name=args.class_name)
    write_jsonl(questions, args.out)

    answers = sum(q.answer_status == "ok" for q in questions)
    print(f"parsed {len(questions)} questions -> {args.out}")
    print(f"  with answer: {answers}   missing answer: {len(questions) - answers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
