import json
from pathlib import Path

from src.generate import validate, verbatim_ratio
from src.satt import parse_questions

ROOT = Path(__file__).resolve().parents[1]


def test_parser_offline():
    html = (ROOT / "data/raw/class8.html").read_text(encoding="utf-8", errors="ignore")
    qs = parse_questions(html, class_name="8")
    assert len(qs) >= 10
    assert all(len(q.options) == 4 for q in qs)
    assert all(q.stem and q.fingerprint for q in qs)
    assert sum(q.answer_status == "ok" for q in qs) >= 5


def test_validator_rejects_bad_items():
    ref = "কোষ হল জীবদেহের ক্ষুদ্রতম গাঠনিক ও কার্যকরী একক। নিউক্লিয়াস কোষের নিয়ন্ত্রণ কেন্দ্র।"
    good = {
        "stem": "কোষের নিয়ন্ত্রণ কেন্দ্র কোনটি?",
        "options": ["নিউক্লিয়াস", "মাইটোকন্ড্রিয়া", "রাইবোজোম", "গলগি বডি"],
        "answer_index": 1,
        "explanation": "নিউক্লিয়াস কোষের কার্যক্রম নিয়ন্ত্রণ করে।",
    }
    assert validate(good, ref) == []

    bad = dict(good, options=["ক", "ক", "গ", "ঘ"])
    assert any("unique" in e for e in validate(bad, ref))

    copied = dict(good, stem="কোষ হল জীবদেহের ক্ষুদ্রতম গাঠনিক ও কার্যকরী একক।")
    assert verbatim_ratio(copied["stem"], ref) > 0.5


if __name__ == "__main__":
    test_parser_offline()
    test_validator_rejects_bad_items()
    print("ok")
