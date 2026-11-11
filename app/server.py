"""Question Paper Studio — local web app (stdlib only).

Run:
    python3 app/server.py            # http://127.0.0.1:8777
    python3 app/server.py --port 9000

The GUI is a static SPA; this module serves it, the JSON API, and PDF export
(via headless Chromium).
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
import traceback
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import db
import paper

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
OUT = ROOT / "out" / "papers"
MAX_BODY = 8 * 1024 * 1024


def now_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def row_to_item(row) -> dict:
    item = dict(row)
    item["options"] = json.loads(item.get("options") or "[]")
    item["subquestions"] = json.loads(item.get("subquestions") or "[]")
    return item


def fetch_items(item_ids: list[str]) -> list[dict]:
    if not item_ids:
        return []
    conn = db.connect()
    try:
        marks = ",".join("?" for _ in item_ids)
        rows = conn.execute(f"SELECT * FROM bank WHERE id IN ({marks})", item_ids).fetchall()
        by_id = {r["id"]: row_to_item(r) for r in rows}
        return [by_id[i] for i in item_ids if i in by_id]
    finally:
        conn.close()


def save_pdf(html_text: str, filename: str) -> Path:
    chrome = next(
        (p for p in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
         if shutil.which(p)),
        None,
    )
    if chrome is None:
        raise RuntimeError("Chromium not found; install chromium or use the browser's Print dialog.")

    work = Path(tempfile.mkdtemp(prefix="qp-", dir="/tmp/opencode"))
    html_path = work / "paper.html"
    html_path.write_text(html_text, encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / filename

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--user-data-dir={work / 'profile'}",
        f"--print-to-pdf={dest}",
        html_path.as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not dest.exists():
        raise RuntimeError((proc.stderr or proc.stdout or "chromium failed").strip()[-500:])
    return dest


class Handler(BaseHTTPRequestHandler):
    server_version = "QPStudio/1.0"

    # ---------- plumbing ----------

    def log_message(self, fmt: str, *args) -> None:
        if not self.path.startswith("/api/") or self.command != "GET":
            print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ValueError("payload too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_file(self, path: Path, download: bool = False) -> None:
        if not path.is_file():
            self.send_error_json(404, "not found")
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)

    # ---------- HTTP verbs ----------

    def do_GET(self) -> None:
        try:
            self.route_get()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.send_error_json(500, str(exc))

    def do_POST(self) -> None:
        try:
            self.route_write("POST")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.send_error_json(500, str(exc))

    def do_PUT(self) -> None:
        try:
            self.route_write("PUT")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.send_error_json(500, str(exc))

    def do_DELETE(self) -> None:
        try:
            self.route_delete()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.send_error_json(500, str(exc))

    # ---------- routing ----------

    def route_get(self) -> None:
        path = unquote(urlparse(self.path).path)

        if path in ("/", "/index.html"):
            self.send_file(STATIC / "index.html")
            return
        if path.startswith("/static/"):
            self.send_file(STATIC / path.removeprefix("/static/"))
            return
        if path.startswith("/files/"):
            self.send_file(OUT / path.removeprefix("/files/"), download=True)
            return
        if path == "/api/meta":
            self.api_meta()
            return
        if path == "/api/questions":
            self.api_questions()
            return
        if path == "/api/papers":
            self.api_papers_list()
            return
        if path.startswith("/api/papers/"):
            self.api_paper_get(path.rsplit("/", 1)[-1])
            return

        self.send_error_json(404, "not found")

    def route_write(self, method: str) -> None:
        path = unquote(urlparse(self.path).path)

        if path == "/api/questions" and method == "POST":
            self.api_question_add()
            return
        if path == "/api/questions/bulk" and method == "POST":
            self.api_questions_bulk()
            return
        if path.startswith("/api/questions/") and method == "PUT":
            self.api_question_update(path.rsplit("/", 1)[-1])
            return
        if path == "/api/papers" and method == "POST":
            self.api_paper_save()
            return
        if path == "/api/preview" and method == "POST":
            self.api_preview()
            return
        if path == "/api/pdf" and method == "POST":
            self.api_pdf()
            return

        self.send_error_json(404, "not found")

    def route_delete(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path.startswith("/api/questions/"):
            self.api_question_delete(path.rsplit("/", 1)[-1])
            return
        if path.startswith("/api/papers/"):
            self.api_paper_delete(path.rsplit("/", 1)[-1])
            return
        self.send_error_json(404, "not found")

    # ---------- API: questions ----------

    def api_meta(self) -> None:
        conn = db.connect()
        try:
            scopes = [
                dict(r) for r in conn.execute(
                    """
                    SELECT class_name, subject, chapter, chapter_title, COUNT(*) AS n
                    FROM bank GROUP BY class_name, subject, chapter, chapter_title
                    ORDER BY class_name, subject, chapter
                    """
                )
            ]
            types = {r["type"]: r["n"] for r in conn.execute(
                "SELECT type, COUNT(*) AS n FROM bank GROUP BY type")}
            blooms = {r["bloom"]: r["n"] for r in conn.execute(
                "SELECT bloom, COUNT(*) AS n FROM bank GROUP BY bloom")}
            total = conn.execute("SELECT COUNT(*) FROM bank").fetchone()[0]
            papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        finally:
            conn.close()
        self.send_json({
            "total": total,
            "papers": papers,
            "scopes": scopes,
            "types": types,
            "blooms": blooms,
        })

    def api_questions(self) -> None:
        qs = parse_qs(urlparse(self.path).query)
        where, args = ["1=1"], []

        def one(name: str):
            vals = qs.get(name)
            return vals[0] if vals and vals[0] else None

        class_name = one("class")
        subject = one("subject")
        chapter = one("chapter")
        bloom = one("bloom")
        if class_name:
            where.append("class_name = ?"); args.append(class_name)
        if subject:
            where.append("subject = ?"); args.append(subject)
        if chapter:
            where.append("chapter = ?"); args.append(chapter)
        if bloom:
            where.append("bloom = ?"); args.append(bloom)

        types = qs.get("type", [])
        if len(types) == 1 and "," in types[0]:
            types = types[0].split(",")
        types = [t for t in types if t]
        if types:
            where.append(f"type IN ({','.join('?' for _ in types)})")
            args.extend(types)

        text = one("q")
        if text:
            where.append("(stem LIKE ? OR answer_text LIKE ? OR stimulus LIKE ?)")
            like = f"%{text}%"
            args.extend([like, like, like])

        limit = min(int(one("limit") or 500), 5000)

        conn = db.connect()
        try:
            rows = conn.execute(
                f"""
                SELECT * FROM bank WHERE {' AND '.join(where)}
                ORDER BY class_name, subject,
                         CAST(chapter AS INTEGER), chapter,
                         CASE type WHEN 'mcq' THEN 1 WHEN 'wrq_k' THEN 2
                                   WHEN 'wrq_kh' THEN 3 ELSE 4 END,
                         id
                LIMIT ?
                """,
                [*args, limit],
            ).fetchall()
        finally:
            conn.close()

        self.send_json({"items": [row_to_item(r) for r in rows], "count": len(rows)})

    def _insert_questions(self, meta: dict, questions: list[dict]) -> int:
        conn = db.connect()
        added = 0
        try:
            for q in questions:
                qid = q.get("id") or f"q-{uuid.uuid4().hex[:12]}"
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO bank
                        (id, class_name, subject, chapter, chapter_title, page, type,
                         stem, stimulus, options, answer_index, answer_text,
                         subquestions, explanation, marks, bloom, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        qid,
                        str(q.get("class_name") or meta.get("class_name") or ""),
                        q.get("subject") or meta.get("subject") or "",
                        str(q.get("chapter") or meta.get("chapter") or ""),
                        q.get("chapter_title") or meta.get("chapter_title") or "",
                        q.get("page") or meta.get("page"),
                        q["type"],
                        q["stem"],
                        q.get("stimulus"),
                        json.dumps(q.get("options") or [], ensure_ascii=False),
                        q.get("answer_index"),
                        q.get("answer_text"),
                        json.dumps(q.get("subquestions") or [], ensure_ascii=False),
                        q.get("explanation"),
                        int(q.get("marks") or 1),
                        q.get("bloom") or "remember",
                        q.get("source") or meta.get("source") or "NCTB",
                    ),
                )
                added += cur.rowcount
            conn.commit()
        finally:
            conn.close()
        return added

    def api_question_add(self) -> None:
        data = self.read_json()
        q = data.get("question") or data
        meta = data.get("meta") or {}
        if not q.get("stem") or not q.get("type"):
            self.send_error_json(400, "stem and type are required")
            return
        self._insert_questions(meta, [q])
        self.send_json({"ok": True})

    def api_questions_bulk(self) -> None:
        data = self.read_json()
        meta = data.get("meta") or {}
        questions = data.get("questions") or []
        if not isinstance(questions, list):
            self.send_error_json(400, "questions must be an array")
            return
        added = self._insert_questions(meta, questions)
        self.send_json({"ok": True, "added": added, "seen": len(questions)})

    def api_question_update(self, qid: str) -> None:
        data = self.read_json()
        q = data.get("question") or data
        fields, args = [], []
        for key in ("stem", "stimulus", "answer_text", "explanation", "bloom",
                    "chapter", "chapter_title", "page"):
            if key in q:
                fields.append(f"{key} = ?"); args.append(q[key])
        if "marks" in q:
            fields.append("marks = ?"); args.append(int(q["marks"]))
        if "type" in q:
            fields.append("type = ?"); args.append(q["type"])
        if "options" in q:
            fields.append("options = ?"); args.append(json.dumps(q["options"], ensure_ascii=False))
        if "answer_index" in q:
            fields.append("answer_index = ?"); args.append(q["answer_index"])
        if "subquestions" in q:
            fields.append("subquestions = ?")
            args.append(json.dumps(q["subquestions"], ensure_ascii=False))
        if not fields:
            self.send_error_json(400, "nothing to update")
            return
        args.append(qid)
        conn = db.connect()
        try:
            conn.execute(f"UPDATE bank SET {', '.join(fields)} WHERE id = ?", args)
            conn.commit()
        finally:
            conn.close()
        self.send_json({"ok": True})

    def api_question_delete(self, qid: str) -> None:
        conn = db.connect()
        try:
            conn.execute("DELETE FROM bank WHERE id = ?", (qid,))
            conn.commit()
        finally:
            conn.close()
        self.send_json({"ok": True})

    # ---------- API: papers ----------

    def api_papers_list(self) -> None:
        conn = db.connect()
        try:
            rows = [dict(r) for r in conn.execute(
                """
                SELECT id, title, total_marks, created_at, updated_at,
                       json_array_length(item_ids) AS n
                FROM papers ORDER BY updated_at DESC
                """
            )]
        finally:
            conn.close()
        self.send_json({"items": rows})

    def api_paper_get(self, pid: str) -> None:
        conn = db.connect()
        try:
            row = conn.execute("SELECT * FROM papers WHERE id = ?", (pid,)).fetchone()
        finally:
            conn.close()
        if row is None:
            self.send_error_json(404, "paper not found")
            return
        item = dict(row)
        item["config"] = json.loads(item["config"])
        item["item_ids"] = json.loads(item["item_ids"])
        self.send_json(item)

    def api_paper_save(self) -> None:
        data = self.read_json()
        title = (data.get("title") or "").strip() or "শিরোনামহীন প্রশ্নপত্র"
        item_ids = data.get("item_ids") or []
        config = data.get("config") or {}
        items = fetch_items(item_ids)
        total = sum(int(i["marks"]) for i in items)
        pid = data.get("id") or f"paper-{uuid.uuid4().hex[:10]}"

        conn = db.connect()
        try:
            conn.execute(
                """
                INSERT INTO papers (id, title, config, item_ids, total_marks)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    config = excluded.config,
                    item_ids = excluded.item_ids,
                    total_marks = excluded.total_marks,
                    updated_at = datetime('now')
                """,
                (
                    pid, title,
                    json.dumps(config, ensure_ascii=False),
                    json.dumps(item_ids, ensure_ascii=False),
                    total,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        self.send_json({"ok": True, "id": pid, "total_marks": total})

    def api_paper_delete(self, pid: str) -> None:
        conn = db.connect()
        try:
            conn.execute("DELETE FROM papers WHERE id = ?", (pid,))
            conn.commit()
        finally:
            conn.close()
        self.send_json({"ok": True})

    # ---------- API: preview / pdf ----------

    def _payload(self) -> tuple[list[dict], dict]:
        data = self.read_json()
        ids = data.get("item_ids") or []
        config = data.get("config") or {}
        if not ids:
            raise ValueError("no questions selected")
        items = fetch_items(ids)
        if not items:
            raise ValueError("selected questions no longer exist")
        return items, config

    def api_preview(self) -> None:
        items, config = self._payload()
        self.send_json({
            "html": paper.render_paper(items, config),
            "count": len(items),
            "total_marks": sum(int(i["marks"]) for i in items),
        })

    def api_pdf(self) -> None:
        items, config = self._payload()
        html_text = paper.render_paper(items, config)
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", (config.get("title") or "paper")).strip("-").lower() or "paper"
        filename = f"{slug[:40]}-{now_slug()}.pdf"
        dest = save_pdf(html_text, filename)
        self.send_json({
            "url": f"/files/{dest.name}",
            "path": str(dest),
            "total_marks": sum(int(i["marks"]) for i in items),
            "count": len(items),
        })


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Question Paper Studio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--reset-seed", action="store_true", help="re-import the demo questions")
    args = ap.parse_args(argv)

    conn = db.connect()
    try:
        db.init(conn)
        if args.reset_seed:
            n = db.seed_bank(conn, force=True)
            print(f"re-seeded {n} questions")
    finally:
        conn.close()

    OUT.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Question Paper Studio → http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
