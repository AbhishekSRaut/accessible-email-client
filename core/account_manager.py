
import keyring
import logging
from typing import List, Optional, Dict
from ..database.db_manager import DBManager

logger = logging.getLogger(__name__)

class AccountManager:
    SERVICE_NAME = "AccessibleEmailClient"

    def __init__(self):
        self.db = DBManager()

    def add_account(self, email: str, password: str, 
                    imap_host: str, imap_port: int, 
                    smtp_host: str, smtp_port: int) -> bool:
        """
        Add a new email account. Stores credentials securely.
        """
        try:
            # Check if account already exists
            existing = self.db.fetch_one("SELECT id FROM accounts WHERE email = ?", (email,))
            if existing:
                logger.warning(f"Account {email} already exists.")
                return False

            # Store password in keyring
            keyring.set_password(self.SERVICE_NAME, email, password)

            # Store account details in DB
            query = """
                INSERT INTO accounts (email, provider_imap_host, provider_imap_port, 
                                      provider_smtp_host, provider_smtp_port)
                VALUES (?, ?, ?, ?, ?)
            """
            self.db.execute_commit(query, (email, imap_host, imap_port, smtp_host, smtp_port))
            
            logger.info(f"Account {email} added successfully.")
            return True

        except Exception as e:
            logger.error(f"Failed to add account {email}: {e}")
            return False

    def update_account(self, old_email: str, new_email: str, password: str, 
                       imap_host: str, imap_port: int, 
                       smtp_host: str, smtp_port: int) -> bool:
        """
        Update an existing account. Handles email address change and password update.
        """
        try:
            # If email changing, check if new email exists
            if old_email != new_email:
                existing = self.db.fetch_one("SELECT id FROM accounts WHERE email = ?", (new_email,))
                if existing:
                    logger.warning(f"Cannot update: Account {new_email} already exists.")
                    return False
            
            # Update DB
            query = """
                UPDATE accounts 
                SET email = ?, provider_imap_host = ?, provider_imap_port = ?, 
                    provider_smtp_host = ?, provider_smtp_port = ?
                WHERE email = ?
            """
            self.db.execute_commit(query, (new_email, imap_host, imap_port, smtp_host, smtp_port, old_email))
            
            # If email changed, update Keyring
            if old_email != new_email:
                # Update Keyring: Delete old, set new
                try:
                    keyring.delete_password(self.SERVICE_NAME, old_email)
                except: pass
                keyring.set_password(self.SERVICE_NAME, new_email, password)
            else:
                # Just update password if changed (or always set it to be safe)
                if password:
                     keyring.set_password(self.SERVICE_NAME, new_email, password)
            
            logger.info(f"Account {old_email} updated successfully (became {new_email}).")
            return True

        except Exception as e:
            logger.error(f"Failed to update account {old_email}: {e}")
            return False

    def get_accounts(self) -> List[Dict]:
        """
        Retrieve all active accounts.
        """
        try:
            rows = self.db.fetch_all("SELECT id, email, provider_imap_host, provider_imap_port, provider_smtp_host, provider_smtp_port FROM accounts WHERE is_active = 1")
            accounts = []
            for row in rows:
                accounts.append({
                    "id": row['id'],
                    "email": row['email'],
                    "imap_host": row['provider_imap_host'],
                    "imap_port": row['provider_imap_port'],
                    "smtp_host": row['provider_smtp_host'],
                    "smtp_port": row['provider_smtp_port']
                })
            return accounts
        except Exception as e:
            logger.error(f"Failed to retrieve accounts: {e}")
            return []

    def get_password(self, email: str) -> Optional[str]:
        """
        Retrieve password from keyring.
        """
        try:
            return keyring.get_password(self.SERVICE_NAME, email)
        except Exception as e:
            logger.error(f"Failed to retrieve password for {email}: {e}")
            return None

    def delete_account(self, email: str) -> bool:
        """
        Delete an account and its credentials.
        """
        try:
            # Remove from DB
            self.db.execute_commit("DELETE FROM accounts WHERE email = ?", (email,))
            
            # Remove from keyring
            try:
                keyring.delete_password(self.SERVICE_NAME, email)
            except keyring.errors.PasswordDeleteError:
                logger.warning(f"Password for {email} not found in keyring during deletion.")

            logger.info(f"Account {email} deleted.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete account {email}: {e}")
            return False
