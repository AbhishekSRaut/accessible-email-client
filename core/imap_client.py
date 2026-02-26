
import logging
from imapclient import IMAPClient as IMAPLib
from ..core.account_manager import AccountManager
from typing import List, Dict, Any, Tuple
import email
from email.header import decode_header

logger = logging.getLogger(__name__)

class IMAPClient:
    def __init__(self, account_email: str):
        self.email = account_email
        self.account_manager = AccountManager()
        self.client = None
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
        Select a folder.
        """
        if not self.client:
            return
        try:
            self.client.select_folder(folder_name, readonly=readonly)
        except Exception as e:
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

            response = self.client.fetch(unique_uids, ['ENVELOPE', 'FLAGS', 'INTERNALDATE'])
            email_map = {}
            for uid, data in response.items():
                envelope = data[b'ENVELOPE']
                email_map[uid] = {
                    "uid": uid,
                    "subject": self._decode_str(envelope.subject),
                    "sender": self._format_address(envelope.from_),
                    "to": self._format_address(envelope.to),
                    "cc": self._format_address(envelope.cc),
                    "date": envelope.date,
                    "flags": [f.decode() if isinstance(f, bytes) else f for f in data[b'FLAGS']],
                    "message_id": self._decode_str(envelope.message_id),
                    "in_reply_to": self._decode_str(envelope.in_reply_to),
                    "references": [], # Missing in envelope
                    "children": []
                }

            # Reconstruct Thread Structure
            result = []
            
            def build_thread_node(node):
                # Handle recursive THREAD tuples: (uid, child1, child2, ...)
                
                if isinstance(node, (list, tuple)):
                    if not node: return None
                    
                    root_uid = node[0]
                    children_nodes = node[1:] if len(node) > 1 else []
                    
                    email_obj = None
                    if isinstance(root_uid, int):
                        email_obj = email_map.get(root_uid)
                    
                    children_objs = []
                    for child_node in children_nodes:
                        child_obj = build_thread_node(child_node)
                        if child_obj:
                            children_objs.append(child_obj)
                            
                    if email_obj:
                        email_obj['children'] = children_objs
                        return email_obj
                    else:
                        return None
                else:
                    # Just a UID?
                    return email_map.get(node)

            # Process top-level threads
            # Reverse to show newest threads first.
            threads_list = list(threads)
            threads_list.reverse()
            
            sliced = threads_list[offset:offset+limit]
            
            for thread_node in sliced:
                thread_obj = build_thread_node(thread_node)
                if thread_obj:
                    result.append(thread_obj)
            
            return result
        except Exception as e:
            logger.error(f"Error fetching threads from {folder_name}: {e}")
            return []

    def _fetch_threads_fallback(self, folder_name: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fallback threading using Message-ID and References headers within the current page.
        This preserves basic thread structure even when THREAD is unsupported.
        """
        if not self.client:
            self._connect()
        if not self.client:
            return []

        try:
            self.select_folder(folder_name, readonly=True)
            messages = self.client.search(['ALL'])
            messages.sort(reverse=True)

            start = offset
            end = offset + limit
            batch_uids = messages[start:end]
            if not batch_uids:
                return []

            fetch_keys = [
                'ENVELOPE',
                'FLAGS',
                'INTERNALDATE',
                'BODY.PEEK[HEADER.FIELDS (MESSAGE-ID REFERENCES IN-REPLY-TO)]'
            ]
            response = self.client.fetch(batch_uids, fetch_keys)

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
                if header_bytes:
                    hdr_msg = email.message_from_bytes(header_bytes)
                    msg_id = (hdr_msg.get('Message-ID') or "").strip()
                    in_reply_to = (hdr_msg.get('In-Reply-To') or "").strip()
                    refs = (hdr_msg.get('References') or "").strip()
                    if refs:
                        references = [r.strip() for r in refs.split() if r.strip()]

                email_map[uid] = {
                    "uid": uid,
                    "subject": self._decode_str(envelope.subject),
                    "sender": self._format_address(envelope.from_),
                    "to": self._format_address(envelope.to),
                    "cc": self._format_address(envelope.cc),
                    "date": envelope.date or internal_date,
                    "flags": [f.decode() if isinstance(f, bytes) else f for f in flags],
                    "children": [],
                    "_msg_id": msg_id,
                    "_in_reply_to": in_reply_to,
                    "_references": references
                }

                if msg_id:
                    msgid_to_uid[msg_id] = uid

            # Build parent-child links
            roots = []
            for uid, email_obj in email_map.items():
                parent_msgid = ""
                if email_obj["_references"]:
                    parent_msgid = email_obj["_references"][-1]
                elif email_obj["_in_reply_to"]:
                    parent_msgid = email_obj["_in_reply_to"]

                parent_uid = msgid_to_uid.get(parent_msgid)
                if parent_uid and parent_uid in email_map and parent_uid != uid:
                    email_map[parent_uid]["children"].append(email_obj)
                else:
                    roots.append(email_obj)

            # Sort roots by date (newest first)
            roots.sort(key=lambda x: x.get("date") or 0, reverse=True)

            # Remove internal fields before returning
            for email_obj in email_map.values():
                email_obj.pop("_msg_id", None)
                email_obj.pop("_in_reply_to", None)
                email_obj.pop("_references", None)

            return roots
        except Exception as e:
            logger.error(f"Fallback threading error for {folder_name}: {e}")
            return self.fetch_emails(folder_name, limit, offset)

    def fetch_email_body(self, folder_name: str, uid: int) -> Dict[str, Any]:
        """
        Fetch the body of a specific email.
        """
        if not self.client:
            self._connect()
            
        if not self.client:
            return {}

        try:
            self.select_folder(folder_name, readonly=True)
            response = self.client.fetch([uid], ['BODY.PEEK[]'])
            raw_email = response[uid][b'BODY[]']
            
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
            logger.error(f"Error fetching body for UID {uid}: {e}")
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

        try:
            # imapclient's move method handles copy + delete + expunge usually, 
            # or uses MOVE extension if available.
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
