import sqlite3
import os
import logging
from typing import List, Tuple, Any, Optional
from ..utils.appdata import get_appdata_dir

logger = logging.getLogger(__name__)

class DBManager:
    """
    Manages SQLite database connections and execution.
    """
    _instance = None
    DB_NAME = "email_client.db"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance._initialize_db()
        return cls._instance

    def _initialize_db(self):
        """
        Initialize the database with the schema if it doesn't exist.
        """
        self.db_path = os.path.join(get_appdata_dir(), self.DB_NAME)
        logger.info(f"Database path: {self.db_path}")

        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        
        if not os.path.exists(self.db_path):
            logger.info("Database file not found. Creating new database.")
            self._create_tables(schema_path)
        else:
            self._create_tables(schema_path)
            self._check_and_migrate()

    def _check_and_migrate(self):
        """
        Check for missing columns and add them.
        """
        try:
            # Check emails table for new columns
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(emails)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if 'in_reply_to' not in columns:
                    logger.info("Migrating: Adding in_reply_to column to emails table")
                    cursor.execute("ALTER TABLE emails ADD COLUMN in_reply_to TEXT")
                    
                if 'references_list' not in columns:
                    logger.info("Migrating: Adding references_list column to emails table")
                    cursor.execute("ALTER TABLE emails ADD COLUMN references_list TEXT")
                    
                conn.commit()
        except Exception as e:
            logger.error(f"Migration failed: {e}")

    def _create_tables(self, schema_path: str):
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
            logger.info("Database schema initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query and return the cursor. 
        Note: This does not commit. Use execute_commit for write operations.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable dictionary cursor for easier access
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor
        except Exception as e:
            logger.error(f"Database execution error: {query} with {params} - {e}")
            raise

    def execute_commit(self, query: str, params: Tuple = ()) -> int:
        """
        Execute a write query and commit. Returns lastrowid.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Database commit error: {query} with {params} - {e}")
            raise

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Database fetch_one error: {query} with {params} - {e}")
            return None

    def fetch_all(self, query: str, params: Tuple = ()) -> List[dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Database fetch_all error: {query} with {params} - {e}")
            return []

    # --- Domain Specific Methods ---

    def upsert_account(self, email, imap_host, imap_port, smtp_host, smtp_port):
        query = """
        INSERT INTO accounts (email, provider_imap_host, provider_imap_port, provider_smtp_host, provider_smtp_port)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            provider_imap_host=excluded.provider_imap_host,
            provider_imap_port=excluded.provider_imap_port,
            provider_smtp_host=excluded.provider_smtp_host,
            provider_smtp_port=excluded.provider_smtp_port
        """
        self.execute_commit(query, (email, imap_host, imap_port, smtp_host, smtp_port))

    def get_account_id(self, email):
        res = self.fetch_one("SELECT id FROM accounts WHERE email = ?", (email,))
        return res['id'] if res else None

    def upsert_folder(self, account_id, name, remote_id=None):
        # Unique constraint is not set in schema for folder name per account, logic handled here just in case
        # Consider adding UNIQUE(account_id, name) to enforce this in the schema.
        res = self.fetch_one("SELECT id FROM folders WHERE account_id = ? AND name = ?", (account_id, name))
        if res:
            return res['id']
        
        return self.execute_commit("INSERT INTO folders (account_id, name, remote_id) VALUES (?, ?, ?)", 
                                   (account_id, name, remote_id or name))

    def get_folder_id(self, account_id, name):
        res = self.fetch_one("SELECT id FROM folders WHERE account_id = ? AND name = ?", (account_id, name))
        return res['id'] if res else None

    def upsert_email(self, account_id, folder_id, uid, subject, sender, date, flags, message_id=None, in_reply_to=None, references=None, body_text=None, body_html=None, recipients=None):
        # We use INSERT OR REPLACE or ON CONFLICT UPDATE
        # Unique constraint on (account_id, folder_id, uid)
        
        query = """
        INSERT INTO emails (account_id, folder_id, uid, subject, sender, date_received, flags, message_id, in_reply_to, references_list, body_text, body_html, recipients)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id, folder_id, uid) DO UPDATE SET
            subject=excluded.subject,
            sender=excluded.sender,
            date_received=excluded.date_received,
            flags=excluded.flags,
            message_id=excluded.message_id,
            in_reply_to=excluded.in_reply_to,
            references_list=excluded.references_list,
            recipients=excluded.recipients
        """
        # If body is provided, update it too. If not (e.g. list fetch), keep existing?
        # Standard list fetch doesn't have body.
        # Only update body when provided.
        
        params = [account_id, folder_id, uid, subject, sender, date, str(flags), message_id, in_reply_to, references, body_text, body_html, recipients]
        
        if body_text is None and body_html is None:
             # Logic to avoid overwriting body with NULL
             query = """
                INSERT INTO emails (account_id, folder_id, uid, subject, sender, date_received, flags, message_id, in_reply_to, references_list, recipients)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, folder_id, uid) DO UPDATE SET
                    subject=excluded.subject,
                    sender=excluded.sender,
                    date_received=excluded.date_received,
                    flags=excluded.flags,
                    message_id=excluded.message_id,
                    in_reply_to=excluded.in_reply_to,
                    references_list=excluded.references_list,
                    recipients=excluded.recipients
            """
             params = [account_id, folder_id, uid, subject, sender, date, str(flags), message_id, in_reply_to, references, recipients]
        elif body_text or body_html:
             # We have body, update it.
             query = """
                INSERT INTO emails (account_id, folder_id, uid, subject, sender, date_received, flags, message_id, in_reply_to, references_list, body_text, body_html, recipients)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, folder_id, uid) DO UPDATE SET
                    subject=excluded.subject,
                    sender=excluded.sender,
                    date_received=excluded.date_received,
                    flags=excluded.flags,
                    message_id=excluded.message_id,
                    in_reply_to=excluded.in_reply_to,
                    references_list=excluded.references_list,
                    body_text=excluded.body_text,
                    body_html=excluded.body_html,
                    recipients=excluded.recipients
             """
        
        self.execute_commit(query, tuple(params))

    def get_emails(self, account_id, folder_id, limit=100, offset=0):
        query = """
        SELECT * FROM emails 
        WHERE account_id = ? AND folder_id = ?
        ORDER BY date_received DESC, uid DESC
        LIMIT ? OFFSET ?
        """
        return self.fetch_all(query, (account_id, folder_id, limit, offset))

    def get_email_body(self, account_id, folder_id, uid):
        return self.fetch_one("SELECT body_text, body_html FROM emails WHERE account_id=? AND folder_id=? AND uid=?", (account_id, folder_id, uid))

    def get_email_flags(self, account_id, folder_id, uid):
        res = self.fetch_one("SELECT flags FROM emails WHERE account_id=? AND folder_id=? AND uid=?", (account_id, folder_id, uid))
        return res["flags"] if res else None

    def update_email_flags(self, account_id, folder_id, uid, flags):
        self.execute_commit("UPDATE emails SET flags = ? WHERE account_id=? AND folder_id=? AND uid=?", (str(flags), account_id, folder_id, uid))

db_manager = DBManager()
