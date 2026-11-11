#!/usr/bin/env python3
"""Build the Android test copy from the main single-file app.

    python3 app/build_android.py

Takes app/question-paper-studio.html, adds the Android-specific meta tags and
touch polish CSS, and writes test-android/question-paper-studio.html.
Run app/build.py first (or run this after any change to src/).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "app/question-paper-studio.html"
OUT = ROOT / "test-android/question-paper-studio.html"

VIEWPORT_OLD = '<meta name="viewport" content="width=device-width, initial-scale=1">'
VIEWPORT_NEW = (
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="theme-color" content="#2f6b3a">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="format-detection" content="telephone=no">'
)

POLISH = """
/* android-test polish */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{-webkit-tap-highlight-color:rgba(47,107,58,.18)}
button,.btn,.chip,.icon{min-height:44px}
.icon{min-width:44px;display:inline-flex;align-items:center;justify-content:center}
input[type=text],input[type=number],select,textarea{font-size:16px;min-height:44px}
.type-num{font-size:16px}
.msel-btn{min-height:44px}
.qcard{padding:13px 14px}
.home-actions .btn{width:min(100%,360px)}
.home h1{padding:.2em .45em .28em;border-radius:15px}
@supports(padding:max(0px)){
  .top-inner{padding-left:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}
  .cartbar{padding-bottom:max(8px,env(safe-area-inset-bottom))}
  .setup,.home,.paper-page{padding-left:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}
}
"""


def main() -> int:
    if not SRC.exists():
        print("main app missing; running build.py", file=sys.stderr)
        subprocess.run([sys.executable, str(ROOT / "app/build.py")], check=True)

    html = SRC.read_text(encoding="utf-8")

    if VIEWPORT_OLD in html and "viewport-fit=cover" not in html:
        html = html.replace(VIEWPORT_OLD, VIEWPORT_NEW)

    if "android-test polish" not in html:
        html = html.replace("</style>", POLISH + "\n</style>", 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"built {OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
