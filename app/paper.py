"""Render a question paper (Bangla, A4) from bank rows + a config dict.

The same HTML is used for the in-app preview and for headless-Chromium PDF
export, so both always look identical.
"""

from __future__ import annotations

import html
from typing import Any

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
OPTION_LETTERS = ["ক", "খ", "গ", "ঘ"]
TYPE_ORDER = ["mcq", "wrq_k", "wrq_kh", "cq"]

SECTIONS = {
    "mcq": ("ক", "বহুনির্বাচনী প্রশ্ন", "সঠিক উত্তরটি উত্তরপত্রে লেখো।"),
    "wrq_k": ("খ", "জ্ঞানমূলক প্রশ্ন", "সংক্ষেপে উত্তর দাও।"),
    "wrq_kh": ("গ", "অনুধাবনমূলক প্রশ্ন", "সংক্ষেপে ব্যাখ্যা করো।"),
    "cq": ("ঘ", "সৃজনশীল প্রশ্ন", "উদ্দীপক পড়ে ক, খ, গ ও ঘ প্রশ্নের উত্তর দাও।"),
}

DEFAULT_INSTRUCTIONS = [
    "প্রশ্নপত্রে মোট প্রদত্ত নম্বরের বিপরীতে উত্তর দিতে হবে।",
    "বহুনির্বাচনী প্রশ্নের একটিমাত্র উত্তর সঠিক; উত্তরপত্রে সঠিক উত্তরটি লেখো।",
    "প্রতিটি প্রশ্নের পাশে নম্বর উল্লেখ করা আছে।",
]


def bn(value: Any) -> str:
    return "".join(BN_DIGITS[int(c)] if c.isdigit() else c for c in str(value))


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _marks_summary(items: list[dict]) -> str:
    if not items:
        return ""
    marks = [int(i["marks"]) for i in items]
    if len(set(marks)) == 1:
        return f"{bn(marks[0])} × {bn(len(marks))} = {bn(sum(marks))}"
    return f"মোট {bn(sum(marks))}"


def _render_mcq_items(items: list[dict]) -> str:
    out = []
    for n, q in enumerate(items, 1):
        options = q.get("options") or []
        longest = max((len(str(o)) for o in options), default=0)
        layout = "two-col" if longest <= 34 else "one-col"
        opts = "".join(
            f'<div><span class="ol">{OPTION_LETTERS[i]}.</span> {esc(o)}</div>'
            for i, o in enumerate(options)
        )
        out.append(
            f'<li><div class="qline"><span class="qt">{esc(q["stem"])}</span>'
            f'<span class="qm">{bn(q["marks"])}</span></div>'
            f'<div class="opts {layout}">{opts}</div></li>'
        )
    return "".join(out)


def _render_wrq_items(items: list[dict]) -> str:
    return "".join(
        f'<li><div class="qline"><span class="qt">{esc(q["stem"])}</span>'
        f'<span class="qm">{bn(q["marks"])}</span></div></li>'
        for q in items
    )


def _render_cq_items(items: list[dict]) -> str:
    out = []
    for q in items:
        subs = "".join(
            f'<div class="sub"><span class="sl">{esc(s.get("label", ""))}.</span> '
            f'<span class="st">{esc(s.get("text", ""))}</span>'
            f'<span class="sm">{bn(s.get("marks", 1))}</span></div>'
            for s in (q.get("subquestions") or [])
        )
        out.append(
            f'<li><div class="stim"><span class="lbl">উদ্দীপক:</span> {esc(q.get("stimulus", ""))}</div>'
            f'<div class="subs">{subs}</div>'
            f'<div class="cqmarks">মোট নম্বর: {bn(q["marks"])}</div></li>'
        )
    return "".join(out)


def _section_html(key: str, items: list[dict]) -> str:
    letter, title, hint = SECTIONS[key]
    if key == "mcq":
        body = f"<ol>{_render_mcq_items(items)}</ol>"
    elif key == "cq":
        body = f"<ol class=\"cqlist\">{_render_cq_items(items)}</ol>"
    else:
        body = f"<ol>{_render_wrq_items(items)}</ol>"
    return (
        f'<section class="sec">'
        f'<h2><span class="sl2">{letter}.</span> {title}'
        f'<span class="sum">{_marks_summary(items)}</span></h2>'
        f'<p class="hint">{hint}</p>{body}</section>'
    )


def _answer_key(items: list[dict], grouped: dict[str, list[dict]]) -> str:
    if not items:
        return ""
    parts = ['<section class="key"><h2>উত্তরমালা</h2>']

    mcq = grouped.get("mcq", [])
    if mcq:
        cells = []
        for i, q in enumerate(mcq, 1):
            idx = q.get("answer_index")
            letter = OPTION_LETTERS[idx - 1] if idx in (1, 2, 3, 4) else "—"
            cells.append(f'<div class="kc"><span>{bn(i)}.</span> {letter}</div>')
        parts.append(f'<h3>বহুনির্বাচনী</h3><div class="kgrid">{"".join(cells)}</div>')

    for key, label in (("wrq_k", "জ্ঞানমূলক"), ("wrq_kh", "অনুধাবনমূলক")):
        rows = grouped.get(key, [])
        if rows:
            items_html = "".join(
                f'<li><span class="kn">{bn(i)}.</span> {esc(q.get("answer_text", "") or "—")}</li>'
                for i, q in enumerate(rows, 1)
            )
            parts.append(f'<h3>{label}</h3><ol class="klist">{items_html}</ol>')

    cqs = grouped.get("cq", [])
    if cqs:
        items_html = "".join(
            f'<li><span class="kn">{bn(i)}.</span> {esc(q.get("answer_text", "") or "—")}</li>'
            for i, q in enumerate(cqs, 1)
        )
        parts.append(f'<h3>সৃজনশীল</h3><ol class="klist">{items_html}</ol>')

    parts.append("</section>")
    return "".join(parts)


def render_paper(items: list[dict], config: dict | None = None) -> str:
    cfg = dict(config or {})
    title = cfg.get("title") or "প্রশ্নপত্র"
    exam_name = cfg.get("exam_name") or ""
    class_label = cfg.get("class_label") or "অষ্টম শ্রেণি"
    subject = cfg.get("subject") or "বিজ্ঞান"
    time_label = cfg.get("time") or "২ ঘণ্টা"
    date_label = cfg.get("date") or ""
    instructions = cfg.get("instructions") or DEFAULT_INSTRUCTIONS
    if isinstance(instructions, str):
        instructions = [line for line in instructions.splitlines() if line.strip()]
    show_key = bool(cfg.get("answer_key", True))
    group = bool(cfg.get("group", True))

    if group:
        ordered = [q for k in TYPE_ORDER for q in items if q["type"] == k]
    else:
        ordered = list(items)

    grouped = {k: [q for q in ordered if q["type"] == k] for k in TYPE_ORDER}
    total = sum(int(q["marks"]) for q in ordered)

    meta_bits = [f"শ্রেণি: {esc(class_label)}", f"বিষয়: {esc(subject)}"]
    if date_label:
        meta_bits.append(f"তারিখ: {esc(date_label)}")
    meta_bits.append(f"সময়: {esc(time_label)}")
    meta_bits.append(f"পূর্ণমান: {bn(total)}")

    sections = "".join(
        _section_html(k, grouped[k]) for k in TYPE_ORDER if grouped[k]
    )

    instr_html = "".join(f"<li>{esc(line)}</li>" for line in instructions)
    key_html = _answer_key(ordered, grouped) if show_key else ""
    exam_html = f'<div class="exam">{esc(exam_name)}</div>' if exam_name else ""

    return f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<style>
  @page {{ size: A4; margin: 14mm 13mm 12mm 13mm; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Serif Bengali', 'Noto Sans Bengali', serif;
    color: #141414; font-size: 10.6pt; line-height: 1.55;
  }}
  @media screen {{
    body {{ background: #e9ece9; padding: 18px 12px 34px; }}
    .paper {{
      width: 794px; max-width: 100%; margin: 0 auto; background: #fff;
      padding: 44px 46px 54px; box-shadow: 0 6px 26px rgba(0,0,0,.14);
    }}
  }}
  @media print {{ .paper {{ width: auto; padding: 0; box-shadow: none; }} }}
  .paper {{ position: relative; }}
  .head {{ text-align: center; border-bottom: 2px solid #234d2d; padding-bottom: 8px; }}
  .exam {{ font-size: 10.5pt; color: #2c2c2c; margin-bottom: 2px; }}
  h1 {{ font-family: 'Noto Sans Bengali', sans-serif; font-size: 17pt; margin: 2px 0 6px; }}
  .meta {{
    display: flex; justify-content: center; flex-wrap: wrap; gap: 4px 20px;
    font-size: 9.8pt;
  }}
  .instr {{
    margin: 10px 0 4px; padding: 7px 10px; background: #f3f6f3;
    border: 1px solid #cfdccf; border-radius: 4px; font-size: 9.2pt;
  }}
  .instr .t {{ font-weight: 700; margin-bottom: 2px; }}
  .instr ol {{ margin: 0; padding-left: 18px; }}
  .sec {{ margin-top: 14px; }}
  h2 {{
    font-family: 'Noto Sans Bengali', sans-serif; font-size: 11.6pt;
    margin: 0 0 2px; padding-bottom: 3px; border-bottom: 1px solid #234d2d;
    display: flex; align-items: baseline; gap: 6px;
  }}
  h2 .sum {{ margin-left: auto; font-size: 9.4pt; font-weight: 400; color: #333; }}
  .hint {{ margin: 2px 0 8px; font-size: 9pt; color: #444; font-style: italic; }}
  ol {{ margin: 0; padding-left: 22px; }}
  li {{ margin: 0 0 9px; break-inside: avoid; }}
  .qline {{ display: flex; gap: 8px; align-items: baseline; }}
  .qt {{ flex: 1; }}
  .qm {{ flex: none; color: #555; font-size: 9pt; min-width: 18px; text-align: right; }}
  .opts {{
    display: grid; gap: 0 22px; margin: 3px 0 0 8px; font-size: 10pt;
  }}
  .opts.two-col {{ grid-template-columns: 1fr 1fr; }}
  .opts.one-col {{ grid-template-columns: 1fr; }}
  .ol {{ color: #234d2d; font-weight: 600; }}
  .stim {{
    border: 1px solid #b9c9b9; background: #f7faf7; border-radius: 3px;
    padding: 6px 9px; margin: 2px 0 6px; font-size: 10pt;
  }}
  .lbl {{ font-weight: 700; color: #234d2d; }}
  .subs {{ padding-left: 4px; }}
  .sub {{ display: flex; gap: 6px; align-items: baseline; margin: 3px 0; }}
  .sl {{ font-weight: 700; color: #234d2d; min-width: 16px; }}
  .st {{ flex: 1; }}
  .sm {{ color: #555; font-size: 9pt; }}
  .cqmarks {{ text-align: right; font-size: 9pt; color: #555; margin-top: 2px; }}
  .cqlist > li {{ margin-bottom: 14px; }}
  .key {{ margin-top: 24px; padding-top: 12px; border-top: 2px solid #234d2d; page-break-before: always; }}
  .key h2 {{ border: 0; }}
  .key h3 {{ font-family: 'Noto Sans Bengali', sans-serif; font-size: 10.6pt; margin: 12px 0 4px; }}
  .kgrid {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px 10px; font-size: 10pt; }}
  .kc span {{ color: #555; }}
  .klist {{ padding-left: 20px; }}
  .kn {{ color: #555; }}
  .foot {{ margin-top: 18px; border-top: 1px solid #ccc; padding-top: 5px; font-size: 8.2pt; color: #666; }}
</style>
</head>
<body>
<div class="paper">
  <div class="head">
    {exam_html}
    <h1>{esc(title)}</h1>
    <div class="meta">{''.join(f'<span>{m}</span>' for m in meta_bits)}</div>
  </div>

  <div class="instr">
    <div class="t">নির্দেশনা</div>
    <ol>{instr_html}</ol>
  </div>

  {sections}
  {key_html}

  <div class="foot">
    উৎস: {esc(cfg.get("source") or "NCTB পাঠ্যপুস্তক")} · প্রশ্নপত্র প্রস্তুতি: Question Paper Studio
  </div>
</div>
</body>
</html>"""
