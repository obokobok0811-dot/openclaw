-- Contacts CRM schema

CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  name TEXT,
  canonical_email TEXT,
  company TEXT,
  role TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
  id INTEGER PRIMARY KEY,
  contact_id INTEGER,
  source TEXT,
  timestamp TIMESTAMP,
  subject TEXT,
  snippet TEXT,
  message_id TEXT,
  thread_id TEXT,
  raw_text TEXT
);

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  contact_id INTEGER,
  box_file_id TEXT,
  box_path TEXT,
  title TEXT,
  url TEXT,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY,
  contact_id INTEGER,
  title TEXT,
  body TEXT,
  due_at TIMESTAMP,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS duplicates (
  id INTEGER PRIMARY KEY,
  contact_a INTEGER,
  contact_b INTEGER,
  score REAL,
  suggested_action TEXT
);
