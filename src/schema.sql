-- Academic question bank schema (SQLite)

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Normalized source items, used for style analysis only.
CREATE TABLE IF NOT EXISTS questions (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    url           TEXT,
    class_name    TEXT,
    subject       TEXT,
    chapter       TEXT,
    stem          TEXT NOT NULL,
    options       TEXT NOT NULL,        -- JSON array
    answer_index  INTEGER,              -- 1..4, NULL if unknown
    answer_text   TEXT,
    tags          TEXT NOT NULL DEFAULT '[]',
    answer_status TEXT NOT NULL,
    fingerprint   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_questions_class ON questions(class_name, subject);

-- Reference passages used to generate new items.
CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,
    doc         TEXT NOT NULL,
    class_name  TEXT,
    subject     TEXT,
    chapter     TEXT,
    page        INTEGER,
    text        TEXT NOT NULL
);

-- Curriculum graph: class -> subject -> chapter, with prerequisites.
CREATE TABLE IF NOT EXISTS nodes (
    id        TEXT PRIMARY KEY,          -- e.g. "8/science/1"
    class_name TEXT NOT NULL,
    subject   TEXT NOT NULL,
    chapter   TEXT NOT NULL,
    title     TEXT,
    ord       INTEGER NOT NULL DEFAULT 0,
    prereqs   TEXT NOT NULL DEFAULT '[]' -- JSON array of node ids
);

-- Generated items (the product).
CREATE TABLE IF NOT EXISTS items (
    id            TEXT PRIMARY KEY,
    node_id       TEXT REFERENCES nodes(id),
    stem          TEXT NOT NULL,
    options       TEXT NOT NULL,        -- JSON array of 4
    answer_index  INTEGER NOT NULL,     -- 1..4
    explanation   TEXT,
    bloom         TEXT,
    difficulty    REAL,
    source_span   TEXT,
    model         TEXT,
    status        TEXT NOT NULL DEFAULT 'draft',  -- draft|approved|rejected
    fingerprint   TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_fp ON items(fingerprint);

CREATE TABLE IF NOT EXISTS attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    correct     INTEGER NOT NULL,
    latency_ms  INTEGER,
    ts          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id, ts);

-- SM-2 state per user/node.
CREATE TABLE IF NOT EXISTS schedule (
    user_id     TEXT NOT NULL,
    node_id     TEXT NOT NULL,
    reps        INTEGER NOT NULL DEFAULT 0,
    ease        REAL NOT NULL DEFAULT 2.5,
    interval_d  INTEGER NOT NULL DEFAULT 0,
    due_at      TEXT,
    last_seen   TEXT,
    mastery     REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (user_id, node_id)
);
