# AGENTS.md — working rules for this repository

## Start of a session

1. Read `HANDOFF.md`. It lists the current state and every unfinished task.
2. Check `git status` and `git log --oneline -5` before editing.

## Project layout

- `app/facts_c3/<code>.py` — curated NCTB fact bases (one module per subject).
  Chapter node keys: `title`, `defs`, `facts`, `groups`, `cq`, `terms`,
  `classes`, `tf_false`, `qa`.
- `app/gen_c3.py` — generator. `SUBJECT_MODULES` decides which subjects run.
- `classes/class-3.json` — combined bank; generated, never hand-edited.
- `app/seed/class3_<code>_all.json` — per-subject output; generated.
- `data/c3_text/` — OCR/text dumps used as reference.

## Rules

- Do not hand-edit generated JSON. Change the fact base or the generator, then
  rerun `python3 app/gen_c3.py` from `app/`.
- Fact-base text for Bengali subjects must stay Bengali-only (the validator
  rejects Latin letters and stray OCR junk). English uses `"script": "en"`,
  Mathematics uses `"script": "math"`.
- Every `facts` entry is `(statement, key)` and `key` must appear verbatim in
  `statement`, otherwise the blank is skipped.
- Keep `tf_false` entries genuinely false; they are the only false statements
  the generator trusts.
- Run `python3 gen_c3.py --report` and `python3 -m tests.test_pipeline` after a
  change. All 74 chapters must keep MCQ / fill / TF / CQ coverage.
- Never commit secrets (`/tmp/opencode/.gh_token`, PATs, device codes).

## End of a session

1. Update `HANDOFF.md` sections 5 (verified) and 6 (pending).
2. Commit the change.
3. Play the completion sound:
   `pw-play /usr/share/sounds/freedesktop/stereo/complete.oga`
