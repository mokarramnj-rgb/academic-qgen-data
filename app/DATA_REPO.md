# Class data repo (on-demand download)

The app itself stays one small offline file. Extra classes are fetched from a
public GitHub repo and then stored **inside the app's own local storage**
(IndexedDB, localStorage fallback), so they keep working offline afterwards.

## Repo

- https://github.com/mokarramnj-rgb/academic-qgen-data
- Raw base (primary): `https://raw.githubusercontent.com/mokarramnj-rgb/academic-qgen-data/main/classes/`
- CDN fallback: `https://cdn.jsdelivr.net/gh/mokarramnj-rgb/academic-qgen-data@main/classes/`

Both are configured in `DATA_SOURCES` at the bottom of `app/src/03-ui.js`.

## File layout

```
classes/class-3.json
classes/class-4.json
...
classes/class-10.json
classes/index.json
```

`class-N.json`:

```json
{
  "meta": {
    "class_name": "3",
    "subject": "বিজ্ঞান",
    "source": "NCTB ...",
    "chapter_map": { "1": "অধ্যায়ের নাম" }
  },
  "questions": [
    {
      "id": "c3s-c1-mcq-001",
      "type": "mcq",
      "stem": "...",
      "options": ["...", "...", "...", "..."],
      "answer_index": 1,
      "answer_text": "...",
      "marks": 1,
      "bloom": "remember",
      "difficulty": 1,
      "chapter": "1"
    }
  ]
}
```

`class_name`, `subject`, `source`, `chapter_title` are optional per question and
fall back to `meta` / `chapter_map`. Question `id`s must be unique across classes.

## App behaviour

- Home shows classes ৩–১০ with checkboxes and one **ডাউনলোড** button.
- Button is **disabled** when every selected class is already in the app.
- Button is **enabled** when at least one selected class is missing.
- Clicking downloads only the missing classes, shows an inline progress bar
  (no modal, no toast), merges the questions into the local bank, persists them,
  and disables the button again.
- Missing file (HTTP 404) → inline text "…পাওয়া যায়নি", button stays enabled.

## Adding a class

1. Add `classes/class-N.json` to the repo (same shape as `class-8.json`).
2. Update `classes/index.json`.
3. `git push` — the app picks it up on the next download click
   (raw.githubusercontent caches for ~5 minutes).

## Regenerating class-8.json from the local seed

```bash
cd /home/moki/academic-qgen
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path('app/seed/class8_science_all.json').read_text(encoding='utf-8'))
meta = dict(d['meta'])
cmap = meta.get('chapter_map') or {}
base = {'class_name': meta.get('class_name','8'), 'subject': meta.get('subject','বিজ্ঞান'), 'source': meta.get('source','NCTB')}
qs = []
for q in d['questions']:
    n = dict(q)
    for k, v in base.items():
        if n.get(k) == v: n.pop(k, None)
    ch = str(n.get('chapter',''))
    if cmap.get(ch) and n.get('chapter_title') == cmap.get(ch): n.pop('chapter_title', None)
    for k in ('stimulus','subquestions','explanation','options'):
        if not n.get(k): n.pop(k, None)
    if n.get('answer_index') is None: n.pop('answer_index', None)
    qs.append(n)
out = {'meta': meta, 'questions': qs}
Path('classes/class-8.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
PY
```
