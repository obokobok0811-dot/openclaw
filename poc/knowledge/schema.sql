-- Knowledge Base schema for SQLite
-- Stores ingested articles with NER entities and embedding references

CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT    UNIQUE NOT NULL,
    title           TEXT,
    content         TEXT,           -- raw HTML content
    cleaned_text    TEXT,           -- cleaned plain text
    summary         TEXT,           -- optional summary
    entities        TEXT,           -- JSON: {"persons":[], "orgs":[], "dates":[], "amounts":[]}
    embedding_id    INTEGER,        -- row index in FAISS index
    source_weight   REAL    DEFAULT 1.0,  -- domain trust weight
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
CREATE INDEX IF NOT EXISTS idx_articles_embedding_id ON articles(embedding_id);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);
