
import logging
from typing import List, Dict, Any, Optional
from ..database.db_manager import db_manager
from ..core.account_manager import AccountManager
from ..core.imap_client import IMAPClient
import json

logger = logging.getLogger(__name__)

class EmailRepository:
    def __init__(self, account_email: str):
        self.email = account_email
        self.imap_client = IMAPClient(account_email)
        self.account_id = db_manager.get_account_id(account_email)
        if not self.account_id:
            # Create account if missing (e.g., legacy DB state).
            am = AccountManager()
            acc = next((a for a in am.get_accounts() if a['email'] == account_email), None)
            if acc:
                db_manager.upsert_account(account_email, acc['imap_host'], acc['imap_port'], acc['smtp_host'], acc['smtp_port'])
                self.account_id = db_manager.get_account_id(account_email)

    def fetch_threads(self, folder_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch threads. Tries IMAP first, falls back to DB.
        """
        # Ensure folder exists in DB.
        folder_id = db_manager.upsert_folder(self.account_id, folder_name)
        
        # Try online first.
        try:
            threads = self.imap_client.fetch_threads(folder_name, limit, offset)
            if threads:
                # Cache threads locally.
                self._cache_threads(folder_id, threads)
                return threads
        except Exception as e:
            logger.warning(f"Online fetch failed for {folder_name}: {e}. Falling back to offline.")
        
        # Fallback to offline cache.
        return self._fetch_threads_from_db(folder_id, limit, offset)

    def get_cached_threads(self, folder_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch threads from local cache only.
        """
        folder_id = db_manager.get_folder_id(self.account_id, folder_name)
        if not folder_id:
            return []
        return self._fetch_threads_from_db(folder_id, limit, offset)

    def fetch_email_body(self, folder_name: str, uid: int) -> Dict[str, Any]:
        """
        Fetch body. Try IMAP, else DB.
        """
        folder_id = db_manager.get_folder_id(self.account_id, folder_name)
        
        # Try online first.
        try:
            body_data = self.imap_client.fetch_email_body(folder_name, uid)
            if body_data:
                # Cache body locally.
                db_manager.upsert_email(
                    self.account_id, folder_id, uid, 
                    subject=body_data.get('headers', {}).get('Subject'),
                    sender=body_data.get('headers', {}).get('From'),
                    date=body_data.get('headers', {}).get('Date'),
                    flags=[],
                    message_id=body_data.get('headers', {}).get('Message-ID'),
                    body_text=body_data.get('text'),
                    body_html=body_data.get('html')
                )
                return body_data
        except Exception as e:
             logger.warning(f"Online body fetch failed: {e}")

        # Fallback to offline cache.
        if folder_id:
            row = db_manager.get_email_body(self.account_id, folder_id, uid)
            if row:
                return {
                    "text": row['body_text'],
                    "html": row['body_html'],
                    "headers": {},
                    "attachments": []
                }
        return {}

    def move_emails(self, uids: List[int], target_folder: str) -> bool:
        # Try online first.
        success = False
        try:
            success = self.imap_client.move_emails(uids, target_folder)
        except:
            logger.warning("Online move failed.")

        # On success, update DB for consistency.
        if success:
            target_folder_id = db_manager.upsert_folder(self.account_id, target_folder)
            # Update folder_id for these emails
            # Direct SQL update
            placeholders = ','.join('?' * len(uids))
            query = f"UPDATE emails SET folder_id = ? WHERE account_id = ? AND uid IN ({placeholders})"
            params = [target_folder_id, self.account_id] + uids
            db_manager.execute_commit(query, tuple(params))
            
        return success

    def delete_emails(self, uids: List[int]) -> bool:
        # Not used directly; EmailListPanel handles delete/move.
        return False

    def add_flags(self, uids: List[int], flags: List[str], folder_name: Optional[str] = None) -> bool:
         # Try online first.
        success = False
        try:
            success = self.imap_client.add_flags(uids, flags)
        except:
            pass
        
        if success:
             if folder_name:
                 folder_id = db_manager.get_folder_id(self.account_id, folder_name)
                 if folder_id:
                     for uid in uids:
                         current = db_manager.get_email_flags(self.account_id, folder_id, uid)
                         current_flags = eval(current) if current else []
                         for f in flags:
                             if f not in current_flags:
                                 current_flags.append(f)
                         db_manager.update_email_flags(self.account_id, folder_id, uid, current_flags)
        return success

    def copy_emails(self, uids: List[int], target_folder: str) -> bool:
        success = False
        try:
            success = self.imap_client.copy_emails(uids, target_folder)
        except:
            logger.warning("Online copy failed.")

        return success

    def remove_flags(self, uids: List[int], flags: List[str], folder_name: Optional[str] = None) -> bool:
        success = False
        try:
            success = self.imap_client.remove_flags(uids, flags)
        except:
            pass

        if success:
            if folder_name:
                folder_id = db_manager.get_folder_id(self.account_id, folder_name)
                if folder_id:
                    for uid in uids:
                        current = db_manager.get_email_flags(self.account_id, folder_id, uid)
                        current_flags = eval(current) if current else []
                        current_flags = [f for f in current_flags if f not in flags]
                        db_manager.update_email_flags(self.account_id, folder_id, uid, current_flags)
        return success

    # --- caching helpers ---

    def _cache_threads(self, folder_id, threads):
        """
        Recursively save threads and children to DB.
        """
        for thread in threads:
            self._save_email_node(folder_id, thread)
    
    def _save_email_node(self, folder_id, email_obj):
        if not email_obj: return
        
        uid = email_obj.get("uid")
        # If uid is None, it might be a container node?
        if not isinstance(uid, int): return

        db_manager.upsert_email(
            self.account_id, 
            folder_id, 
            uid,
            subject=email_obj.get("subject"),
            sender=email_obj.get("sender"),
            date=email_obj.get("date"),
            flags=email_obj.get("flags"),
            message_id=email_obj.get("_msg_id"),     # These keys come from _fetch_threads_fallback
            in_reply_to=email_obj.get("_in_reply_to"),
            references=json.dumps(email_obj.get("_references", [])),
            body_text=None, # List fetch doesn't have body
            body_html=None
        )
        
        for child in email_obj.get("children", []):
            self._save_email_node(folder_id, child)

    def _fetch_threads_from_db(self, folder_id, limit, offset):
        """
        Reconstruct threads from flat DB rows.
        """
        rows = db_manager.get_emails(self.account_id, folder_id, limit, offset)
        if not rows:
            return []
            
        # Convert rows to dicts
        email_map = {}
        for row in rows:
            uid = row['uid']
            email_map[uid] = {
                "uid": uid,
                "subject": row['subject'],
                "sender": row['sender'],
                "date": row['date_received'],
                "flags": eval(row['flags']) if row['flags'] else [], # unsafe eval? flags is list repr str
                "children": [],
                "_msg_id": row['message_id'],
                "_in_reply_to": row['in_reply_to'],
                "_references": json.loads(row['references_list']) if row['references_list'] else []
            }

        # Build threads (similar to imap_client fallback)
        # However, `get_emails` only returns a page. 
        # Threading might require parents that are NOT in this page?
        # True. Offline threading is hard if we don't have all data.
        # ImapClient fallback fetches a batch and threads WITHIN that batch.
        # We will do the same for DB.
        
        roots = []
        # Create a lookup for children linking
        # Since we only have a slice, we can only link within valid UIDs.
        
        # Link children
        # Improve: Sort by date first to ensure parents come before children? 
        # DB returns by Date DESC.
        
        # Since we scan list, we can link.
        # But wait, parent might be in DB but not in this 'rows' slice?
        # If so, we treat child as root?
        # Yes, standard behavior for partial view.
        
        # We can map Message-ID to UID for linking if we had all UIDs.
        # Here we only have rows.
        
        # Mapping by MessageID within valid rows
        msgid_to_uid = {}
        for uid, obj in email_map.items():
            if obj["_msg_id"]:
                msgid_to_uid[obj["_msg_id"]] = uid
                
        for uid, obj in email_map.items():
            parent_msgid = ""
            if obj["_references"]:
                parent_msgid = obj["_references"][-1]
            elif obj["_in_reply_to"]:
                parent_msgid = obj["_in_reply_to"]
            
            parent_uid = msgid_to_uid.get(parent_msgid)
            if parent_uid and parent_uid in email_map and parent_uid != uid:
                email_map[parent_uid]["children"].append(obj)
            else:
                roots.append(obj)
                
        return roots
