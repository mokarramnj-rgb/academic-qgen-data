-- Question Paper Studio: app database
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS bank (
    id            TEXT PRIMARY KEY,
    class_name    TEXT NOT NULL,
    subject       TEXT NOT NULL,
    chapter       TEXT NOT NULL DEFAULT '',
    chapter_title TEXT NOT NULL DEFAULT '',
    page          INTEGER,
    type          TEXT NOT NULL CHECK (type IN ('mcq', 'wrq_k', 'wrq_kh', 'cq')),
    stem          TEXT NOT NULL,
    stimulus      TEXT,
    options       TEXT NOT NULL DEFAULT '[]',   -- JSON array
    answer_index  INTEGER,                      -- 1..4 for mcq
    answer_text   TEXT,
    subquestions  TEXT NOT NULL DEFAULT '[]',   -- JSON [{label,text,marks}]
    explanation   TEXT,
    marks         INTEGER NOT NULL,
    bloom         TEXT NOT NULL DEFAULT 'remember',
    source        TEXT NOT NULL DEFAULT 'NCTB',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bank_scope ON bank(class_name, subject, chapter);
CREATE INDEX IF NOT EXISTS idx_bank_type  ON bank(type);

CREATE TABLE IF NOT EXISTS papers (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    config      TEXT NOT NULL,          -- JSON
    item_ids    TEXT NOT NULL,          -- JSON array, ordered
    total_marks INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
