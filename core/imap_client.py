
import logging
import threading
from imapclient import IMAPClient as IMAPLib
from ..core.account_manager import AccountManager
from typing import List, Dict, Any, Tuple
import email
import email.utils
from email.header import decode_header

logger = logging.getLogger(__name__)

import re

class IMAPClient:
    def __init__(self, account_email: str):
        self.email = account_email
        self.account_manager = AccountManager()
        self.client = None
        self.imap_host = ""
        self._lock = threading.Lock()
        self._selected_folder = None
        self._selected_readonly = None
        self._connect()

    def _connect(self):
        """
        Connects to the IMAP server.
        """
        accounts = self.account_manager.get_accounts()
        account = next((a for a in accounts if a['email'] == self.email), None)
        
        if not account:
            logger.error(f"Account {self.email} not found.")
            return

        try:
            password = self.account_manager.get_password(self.email)
            if not password:
                logger.error(f"No password found for {self.email}")
                return

            self.imap_host = account['imap_host']
            self.client = IMAPLib(account['imap_host'], port=account['imap_port'], ssl=True)
            self.client.login(self.email, password)
            logger.info(f"Logged in to {self.email}")
        except Exception as e:
            logger.error(f"Failed to connect to IMAP for {self.email}: {e}")
            self.client = None

    def list_folders(self) -> List[Dict[str, Any]]:
        """
        List all folders on the server.
        """
        if not self.client:
            self._connect()
        
        if not self.client:
            return []

        try:
            folders = self.client.list_folders()
            # folders is a list of (flags, delimiter, name)
            result = []
            for flags, delimiter, name in folders:
                result.append({
                    "name": name,
                    "flags": flags,
                    "delimiter": delimiter
                })
            return result
        except Exception as e:
            logger.error(f"Error listing folders for {self.email}: {e}")
            return []

    def select_folder(self, folder_name: str, readonly: bool = False):
        """
        Select a folder. Tracks current selection to avoid redundant selects.
        The caller MUST hold self._lock when calling this method.
        """
        if not self.client:
            return
        try:
            # Skip re-select if already on the same folder with same mode
            if self._selected_folder == folder_name and self._selected_readonly == readonly:
                return
            self.client.select_folder(folder_name, readonly=readonly)
            self._selected_folder = folder_name
            self._selected_readonly = readonly
            logger.debug(f"Selected folder '{folder_name}' (readonly={readonly})")
        except Exception as e:
            self._selected_folder = None
            self._selected_readonly = None
            logger.error(f"Error selecting folder {folder_name}: {e}")

    def create_folder(self, folder_name: str) -> bool:
        """
        Create a new folder.
        """
        if not self.client:
            self._connect()
        if not self.client:
            return False
            
        try:
            self.client.create_folder(folder_name)
            return True
        except Exception as e:
            logger.error(f"Error creating folder {folder_name}: {e}")
            return False

    def fetch_emails(self, folder_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch emails from the selected folder.
        Uses UIDs.
        """
        if not self.client:
            self._connect()
        
        if not self.client:
            return []

        try:
            self.select_folder(folder_name, readonly=True)
            messages = self.client.search(['ALL'])
            messages.sort(reverse=True) # Newest first
            
            start = offset
            end = offset + limit
            batch_uids = messages[start:end]

            if not batch_uids:
                return []

            # content_data = self.client.fetch(batch_uids, ['BODY.PEEK[]']) # Takes too much bandwidth, just headers first
            # We want ENVELOPE and FLAGS
            response = self.client.fetch(batch_uids, ['ENVELOPE', 'FLAGS', 'INTERNALDATE', 'BODYSTRUCTURE'])
            
            emails = []
            for uid, data in response.items():
                envelope = data[b'ENVELOPE']
                
                # Decode subject
                subject = self._decode_str(envelope.subject)
                sender = self._format_address(envelope.from_)
                to = self._format_address(envelope.to)
                cc = self._format_address(envelope.cc)
                date = envelope.date
                flags = data[b'FLAGS']
                
                # Extract Threading Info
                message_id = self._decode_str(envelope.message_id)
                in_reply_to = self._decode_str(envelope.in_reply_to)

                emails.append({
                    "uid": uid,
                    "subject": subject,
                    "sender": sender,
                    "to": to,
                    "cc": cc,
                    "date": date,
                    "flags": [f.decode() if isinstance(f, bytes) else f for f in flags],
                    "message_id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": [] 
                })
            
            return emails
        except Exception as e:
            logger.error(f"Error fetching emails from {folder_name}: {e}")
            return []

    def fetch_threads(self, folder_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch emails as threads.
        Returns a list where each item is a thread root (email dict).
        Thread roots may have a 'children' key containing a list of replies.
        """
        if not self.client:
            self._connect()
        
        if not self.client:
            return []

        with self._lock:
          try:
            self.select_folder(folder_name, readonly=True)
            
            # Fetch threaded UIDs
            try:
                # Returns nested tuples: ((uid, (reply1, reply2)), ...)
                # Example: ((1, (2,)), (3,))
                threads = self.client.thread(algorithm='REFERENCES', criteria='ALL')
            except Exception as e:
                logger.warning(f"THREAD command failed, falling back to header-based threading: {e}")
                return self._fetch_threads_fallback(folder_name, limit, offset)

            if not threads:
                return []
            
            # Flatten to fetch envelopes
            all_uids = []
            def extract_uids(node):
                if isinstance(node, (list, tuple)):
                    for item in node:
                        extract_uids(item)
                else:
                    if node: # simple uid
                        all_uids.append(node)
            
            extract_uids(threads)
            
            # Fetch Metadata (batch)
            # Fetch ENVELOPE, FLAGS, INTERNALDATE for all UIDs in threads
            # Filter duplicates if any
            unique_uids = list(set(all_uids))
            if not unique_uids:
                return []

            response = self.client.fetch(unique_uids, ['ENVELOPE', 'FLAGS', 'INTERNALDATE', 'BODY.PEEK[HEADER.FIELDS (DATE)]'])
            email_map = {}
            for uid, data in response.items():
                envelope = data[b'ENVELOPE']

                # Parse Date header for timezone-aware datetime
                parsed_date = None
                for key in data.keys():
                    if isinstance(key, bytes) and b'HEADER.FIELDS' in key:
                        try:
                            hdr_msg = email.message_from_bytes(data[key])
                            date_str = hdr_msg.get('Date', '')
                            if date_str:
                                parsed_date = email.utils.parsedate_to_datetime(date_str)
                        except Exception:
                            pass
                        break

                email_map[uid] = {
                    "uid": uid,
                    "subject": self._decode_str(envelope.subject),
                    "sender": self._format_address(envelope.from_),
                    "to": self._format_address(envelope.to),
                    "cc": self._format_address(envelope.cc),
                    "date": parsed_date or data.get(b'INTERNALDATE') or envelope.date,
                    "flags": [f.decode() if isinstance(f, bytes) else f for f in data[b'FLAGS']],
                    "message_id": self._decode_str(envelope.message_id),
                    "in_reply_to": self._decode_str(envelope.in_reply_to),
                    "references": [], # Missing in envelope
                    "children": []
                }

            # Reconstruct Thread Structure
            result = []
            
            def build_thread_node(node):
                # Handle THREAD tuples: (uid1, uid2, uid3, ...) means uid1→uid2→uid3 chain
                # Also handles nested: (uid1, (uid2, uid3)) 
                
                if isinstance(node, (list, tuple)):
                    if not node: return None
                    
                    # Collect all items: ints are UIDs, tuples are sub-threads
                    items = list(node)
                    
                    # Build a chain: first int UID is root, subsequent ints are chained children
                    root_obj = None
                    current_parent = None
                    
                    for item in items:
                        if isinstance(item, int):
                            obj = email_map.get(item)
                            if obj:
                                obj['children'] = []
                                if root_obj is None:
                                    root_obj = obj
                                    current_parent = obj
                                else:
                                    current_parent['children'].append(obj)
                                    current_parent = obj
                        elif isinstance(item, (list, tuple)):
                            # Nested sub-thread
                            child_obj = build_thread_node(item)
                            if child_obj and current_parent:
                                current_parent['children'].append(child_obj)
                            elif child_obj:
                                root_obj = child_obj
                                current_parent = child_obj
                    
                    return root_obj
                else:
                    # Just a UID
                    obj = email_map.get(node)
                    if obj:
                        obj['children'] = []
                    return obj

            # Process ALL top-level threads first (no slicing yet)
            threads_list = list(threads)
            
            for thread_node in threads_list:
                thread_obj = build_thread_node(thread_node)
                if thread_obj:
                    result.append(thread_obj)
            
            # Merge orphan roots by subject across ALL threads
            result = self._merge_by_subject(result)

            # NOW paginate on the merged thread list
            return result[offset:offset+limit]
          except Exception as e:
            logger.error(f"Error fetching threads from {folder_name}: {e}")
            return []

    @staticmethod
    def _normalize_subject(subject: str) -> str:
        """Strip Re:/Fwd:/FW: prefixes and whitespace for subject-based grouping."""
        if not subject:
            return ""
        # Repeatedly strip common prefixes
        s = subject.strip()
        pattern = re.compile(r'^\s*(re|fwd|fw)\s*:\s*', re.IGNORECASE)
        while pattern.match(s):
            s = pattern.sub('', s, count=1).strip()
        return s.lower()

    @classmethod
    def _merge_by_subject(cls, roots: List[Dict]) -> List[Dict]:
        """
        Post-process thread roots: merge single-item roots with matching
        normalized subjects into a single thread (oldest as root).
        This catches mailing-list threads that the server didn't group.
        """
        subject_groups = {}  # normalized_subject -> [root_obj, ...]
        final_roots = []

        for root_obj in roots:
            norm_subj = cls._normalize_subject(root_obj.get("subject", ""))
            if norm_subj and len(norm_subj) > 3:  # Ignore very short subjects
                subject_groups.setdefault(norm_subj, []).append(root_obj)
            else:
                final_roots.append(root_obj)

        for norm_subj, group in subject_groups.items():
            if len(group) == 1:
                final_roots.append(group[0])
            else:
                # Multiple messages — group under the oldest as root
                group.sort(key=lambda x: x.get("date") or 0)
                thread_root = group[0]
                for sibling in group[1:]:
                    # Move sibling's existing children to root if any
                    thread_root["children"].extend(sibling.get("children", []))
                    sibling["children"] = []
                    thread_root["children"].append(sibling)
                final_roots.append(thread_root)

        # Sort by newest date in thread
        def thread_newest_date(root):
            dates = [root.get("date") or 0]
            for c in root.get("children", []):
                dates.append(c.get("date") or 0)
            return max(dates)

        final_roots.sort(key=thread_newest_date, reverse=True)
        return final_roots

    def _is_gmail(self) -> bool:
        """Check if the connected server is Gmail."""
        return 'gmail' in self.imap_host.lower() or 'google' in self.imap_host.lower()

    def _fetch_threads_fallback(self, folder_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fallback threading using three tiers:
        1. Gmail X-GM-THRID (native thread ID) when available
        2. In-Reply-To / References header linking
        3. Subject-based grouping for remaining orphans
        NOTE: Caller (fetch_threads) already holds self._lock.
        """
        if not self.client:
            self._connect()
        if not self.client:
            return []

        try:
            self.select_folder(folder_name, readonly=True)
            messages = self.client.search(['ALL'])
            messages.sort(reverse=True)

            if not messages:
                return []

            # Determine fetch keys based on server capabilities
            use_gmail_threads = self._is_gmail()
            fetch_keys = [
                'ENVELOPE',
                'FLAGS',
                'INTERNALDATE',
                'BODY.PEEK[HEADER.FIELDS (DATE MESSAGE-ID REFERENCES IN-REPLY-TO)]'
            ]
            if use_gmail_threads:
                fetch_keys.append('X-GM-THRID')

            # Fetch ALL emails for cross-page threading
            response = self.client.fetch(messages, fetch_keys)

            email_map = {}
            msgid_to_uid = {}

            for uid, data in response.items():
                envelope = data[b'ENVELOPE']
                flags = data[b'FLAGS']
                internal_date = data.get(b'INTERNALDATE')

                header_bytes = None
                for key in data.keys():
                    if isinstance(key, bytes) and b'HEADER.FIELDS' in key:
                        header_bytes = data[key]
                        break

                msg_id = ""
                in_reply_to = ""
                references = []
                parsed_date = None
                if header_bytes:
                    hdr_msg = email.message_from_bytes(header_bytes)
                    msg_id = (hdr_msg.get('Message-ID') or "").strip()
                    in_reply_to = (hdr_msg.get('In-Reply-To') or "").strip()
                    refs = (hdr_msg.get('References') or "").strip()
                    if refs:
                        references = [r.strip() for r in refs.split() if r.strip()]
                    # Parse Date header for timezone-aware datetime
                    date_str = hdr_msg.get('Date', '')
                    if date_str:
                        try:
                            parsed_date = email.utils.parsedate_to_datetime(date_str)
                        except Exception:
                            pass

                # Gmail thread ID
                gm_thrid = data.get(b'X-GM-THRID') if use_gmail_threads else None

                email_map[uid] = {
                    "uid": uid,
                    "subject": self._decode_str(envelope.subject),
                    "sender": self._format_address(envelope.from_),
                    "to": self._format_address(envelope.to),
                    "cc": self._format_address(envelope.cc),
                    "date": parsed_date or internal_date or envelope.date,
                    "flags": [f.decode() if isinstance(f, bytes) else f for f in flags],
                    "children": [],
                    "_msg_id": msg_id,
                    "_in_reply_to": in_reply_to,
                    "_references": references,
                    "_gm_thrid": gm_thrid
                }

                if msg_id:
                    msgid_to_uid[msg_id] = uid

            # === TIER 1: Gmail X-GM-THRID grouping ===
            if use_gmail_threads:
                thrid_groups = {}  # thrid -> [uid, uid, ...]
                for uid, obj in email_map.items():
                    thrid = obj.get("_gm_thrid")
                    if thrid:
                        thrid_groups.setdefault(thrid, []).append(uid)

                roots = []
                used_uids = set()

                for thrid, uids in thrid_groups.items():
                    # Sort by date ascending so oldest is root
                    uids.sort(key=lambda u: email_map[u].get("date") or 0)
                    root_uid = uids[0]
                    root_obj = email_map[root_uid]
                    root_obj["children"] = []
                    for child_uid in uids[1:]:
                        child_obj = email_map[child_uid]
                        child_obj["children"] = []
                        root_obj["children"].append(child_obj)
                    roots.append(root_obj)
                    used_uids.update(uids)

                # Add any emails without X-GM-THRID as standalone roots
                for uid, obj in email_map.items():
                    if uid not in used_uids:
                        obj["children"] = []
                        roots.append(obj)

                # Sort roots by newest message date (considering children)
                def thread_newest_date(root):
                    dates = [root.get("date") or 0]
                    for c in root.get("children", []):
                        dates.append(c.get("date") or 0)
                    return max(dates)

                roots.sort(key=thread_newest_date, reverse=True)

                # Clean internal fields
                for obj in email_map.values():
                    obj.pop("_msg_id", None)
                    obj.pop("_in_reply_to", None)
                    obj.pop("_references", None)
                    obj.pop("_gm_thrid", None)

                # Post-process: merge orphan roots by subject, then paginate
                merged = self._merge_by_subject(roots)
                return merged[offset:offset+limit]

            # === TIER 2: In-Reply-To / References header linking ===
            linked_uids = set()  # UIDs that got linked as children
            roots = []
            for uid, email_obj in email_map.items():
                parent_msgid = ""
                if email_obj["_references"]:
                    # Try all references, not just the last one
                    for ref in reversed(email_obj["_references"]):
                        if ref in msgid_to_uid and msgid_to_uid[ref] != uid:
                            parent_msgid = ref
                            break
                if not parent_msgid and email_obj["_in_reply_to"]:
                    parent_msgid = email_obj["_in_reply_to"]

                parent_uid = msgid_to_uid.get(parent_msgid)
                if parent_uid and parent_uid in email_map and parent_uid != uid:
                    email_map[parent_uid]["children"].append(email_obj)
                    linked_uids.add(uid)
                else:
                    roots.append(email_obj)

            # === TIER 3: Subject-based grouping for remaining orphan roots ===
            final_roots = self._merge_by_subject(roots)

            # Remove internal fields before returning
            for email_obj in email_map.values():
                email_obj.pop("_msg_id", None)
                email_obj.pop("_in_reply_to", None)
                email_obj.pop("_references", None)
                email_obj.pop("_gm_thrid", None)

            return final_roots[offset:offset+limit]
        except Exception as e:
            logger.error(f"Fallback threading error for {folder_name}: {e}")
            return self.fetch_emails(folder_name, limit, offset)

    def fetch_email_body(self, folder_name: str, uid: int) -> Dict[str, Any]:
        """
        Fetch the body of a specific email.
        Uses lock to prevent concurrent folder re-selection.
        """
        if not self.client:
            self._connect()
            
        if not self.client:
            return {}

        with self._lock:
          try:
            self.select_folder(folder_name, readonly=True)
            logger.debug(f"Fetching body for UID {uid} in folder '{folder_name}'")
            response = self.client.fetch([uid], ['BODY.PEEK[]'])
            
            if uid not in response:
                logger.warning(f"UID {uid} not found in folder '{folder_name}' response")
                return {}
            
            raw_data = response[uid]
            if b'BODY[]' not in raw_data:
                logger.warning(f"No BODY[] data for UID {uid} in folder '{folder_name}'")
                return {}
            
            raw_email = raw_data[b'BODY[]']
            
            msg = email.message_from_bytes(raw_email)
            body_text = ""
            body_html = ""
            attachments = []
            headers = {
                "From": msg.get("From", ""),
                "To": msg.get("To", ""),
                "Cc": msg.get("Cc", ""),
                "Subject": self._decode_str(msg.get("Subject", "")),
                "Date": msg.get("Date", ""),
                "Message-ID": msg.get("Message-ID", ""),
                "References": msg.get("References", ""),
                "In-Reply-To": msg.get("In-Reply-To", "")
            }

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    filename = part.get_filename()

                    payload = part.get_payload(decode=True)
                    if payload:
                        if "attachment" in content_disposition or filename:
                            attachments.append({
                                "filename": filename or "attachment",
                                "content_type": content_type,
                                "data": payload
                            })
                        else:
                            decoded = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
                            if content_type == "text/plain":
                                body_text += decoded
                            elif content_type == "text/html":
                                body_html += decoded
            else:
                payload = msg.get_payload(decode=True)
                decoded = payload.decode(msg.get_content_charset() or 'utf-8', errors='replace')
                if msg.get_content_type() == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded
            
            return {
                "text": body_text,
                "html": body_html,
                "headers": headers,
                "attachments": attachments
            }

          except Exception as e:
            logger.error(f"Error fetching body for UID {uid} in folder '{folder_name}': {e}")
            return {}

    def _decode_str(self, header_val):
        if not header_val:
            return ""
        if isinstance(header_val, bytes):
            return header_val.decode('utf-8', errors='replace')
        
        decoded_list = decode_header(str(header_val))
        result = ""
        for token, charset in decoded_list:
            if isinstance(token, bytes):
                if charset:
                    result += token.decode(charset, errors='replace')
                else:
                    result += token.decode('utf-8', errors='replace')
            else:
                result += str(token)
        return result

    def _format_address(self, addresses):
        if not addresses:
            return ""
        # addresses is a tuple of (name, route, mailbox, host)
        # simplistic implementation
        result = []
        for addr in addresses:
            name = self._decode_str(addr.name) if addr.name else ""
            email_addr = f"{self._decode_str(addr.mailbox)}@{self._decode_str(addr.host)}"
            if name:
                result.append(f"{name} <{email_addr}>")
            else:
                result.append(email_addr)
        return ", ".join(result)

    def move_emails(self, uids: List[int], target_folder: str) -> bool:
        """
        Move emails to another folder.
        """
        if not self.client:
            self._connect()
        if not self.client:
            return False

        with self._lock:
          try:
            # imapclient's move method handles copy + delete + expunge usually, 
            # or uses MOVE extension if available.
            self._selected_folder = None  # folder state changes after move
            self.client.move(uids, target_folder)
            return True
          except Exception as e:
            logger.error(f"Error moving emails to {target_folder}: {e}")
            return False

    def copy_emails(self, uids: List[int], target_folder: str) -> bool:
        """
        Copy emails to another folder.
        """
        if not self.client:
            self._connect()
        if not self.client:
            return False

        with self._lock:
          try:
            self.client.copy(uids, target_folder)
            return True
          except Exception as e:
            logger.error(f"Error copying emails to {target_folder}: {e}")
            return False

    def add_flags(self, uids: List[int], flags: List[str]) -> bool:
        r"""
        Add flags to emails (e.g. \Seen).
        """
        if not self.client:
            self._connect()
        if not self.client:
            return False
            
        with self._lock:
          try:
            self.client.add_flags(uids, flags)
            return True
          except Exception as e:
            logger.error(f"Error adding flags {flags}: {e}")
            return False

    def remove_flags(self, uids: List[int], flags: List[str]) -> bool:
        """
        Remove flags from emails.
        """
        if not self.client:
            self._connect()
        if not self.client:
            return False
            
        with self._lock:
          try:
            self.client.remove_flags(uids, flags)
            return True
          except Exception as e:
            logger.error(f"Error removing flags {flags}: {e}")
            return False

    def logout(self):
        if self.client:
            try:
                self.client.logout()
            except:
                pass
            self.client = None
