-- Database Schema for Accessible Email Client

-- Accounts Table
-- Stores configuration for email accounts. Passwords are NOT stored here (use keyring).
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    provider_imap_host TEXT NOT NULL,
    provider_imap_port INTEGER NOT NULL,
    provider_smtp_host TEXT NOT NULL,
    provider_smtp_port INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Folders Table
-- Represents mail folders/labels for each account.
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    remote_id TEXT, -- The folder name on the server (e.g., "[Gmail]/All Mail")
    parent_id INTEGER,
    type TEXT, -- 'inbox', 'sent', 'trash', 'drafts', 'custom'
    message_count INTEGER DEFAULT 0,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Emails Table
-- Caches email metadata and content reference.
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    folder_id INTEGER NOT NULL,
    uid INTEGER NOT NULL, -- IMAP UID
    message_id TEXT, -- Message-ID header
    in_reply_to TEXT, -- In-Reply-To header
    references_list TEXT, -- References header (renamed to avoid keyword conflict if any, though "references" is SQL keyword)
    subject TEXT,
    sender TEXT,
    recipients TEXT, -- Comma separated list
    date_received TIMESTAMP,
    flags TEXT, -- JSON or comma separated flags (Seen, Answered, etc.)
    content_path TEXT, -- Path to local content file if stored externally, or NULL if in DB
    body_text TEXT, -- Plain text body preview
    body_html TEXT, -- HTML body content (if needed in DB)
    is_read BOOLEAN DEFAULT 0,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE,
    UNIQUE(account_id, folder_id, uid)
);

-- Rules Table
-- Stores smart folder rules.
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    condition_json TEXT NOT NULL, -- e.g., {"sender": "foo@bar.com"}
    action_json TEXT NOT NULL, -- e.g., {"move_to": "Family"}
    is_active BOOLEAN DEFAULT 1
);
