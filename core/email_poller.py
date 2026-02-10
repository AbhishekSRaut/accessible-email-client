
import threading
import time
import logging
from ..core.account_manager import AccountManager
from ..core.imap_client import IMAPClient
from ..core.notification_manager import notification_manager

logger = logging.getLogger(__name__)

class EmailPoller(threading.Thread):
    def __init__(self, interval=60):
        super().__init__()
        self.interval = interval
        self.running = False
        self.account_manager = AccountManager()
        self.last_uids = {} # {email: last_seen_uid}
        self.daemon = True # Daemon thread exits when main program exits

    def run(self):
        self.running = True
        logger.info("Email Poller started.")
        
        # Initial sync - just get current max UIDs without notifying
        self._sync_initial_uids()
        
        while self.running:
            try:
                time.sleep(self.interval)
                self._poll_accounts()
            except Exception as e:
                logger.error(f"Error in EmailPoller loop: {e}")

    def stop(self):
        self.running = False

    def _sync_initial_uids(self):
        accounts = self.account_manager.get_accounts()
        for acc in accounts:
            email_addr = acc['email']
            try:
                client = IMAPClient(email_addr)
                # Select Inbox
                client.select_folder('INBOX', readonly=True)
                
                # Get all UIDs
                # We need to access the underlying client to get max UID efficiently
                # or use search(['ALL'])
                if client.client:
                    # imapclient search returns list of UIDs
                    uids = client.client.search(['ALL'])
                    if uids:
                        self.last_uids[email_addr] = max(uids)
                    else:
                        self.last_uids[email_addr] = 0
                client.logout()
            except Exception as e:
                logger.error(f"Failed to sync initial UID for {email_addr}: {e}")

    def _poll_accounts(self):
        accounts = self.account_manager.get_accounts()
        for acc in accounts:
            email_addr = acc['email']
            last_uid = self.last_uids.get(email_addr, 0)
            
            try:
                client = IMAPClient(email_addr)
                client.select_folder('INBOX', readonly=True)
                
                if not client.client:
                    continue

                # Search for new UIDs
                # UID criteria: UID > last_uid
                # IMAP command: UID start:star
                # But start must be last_uid + 1
                search_crit = f"{last_uid + 1}:*"
                
                # We can't use UID X:* if X is larger than any existing UID, it might return nothing or the last one?
                # Actually UID NEXT is better but standardized search is UID val:*
                
                new_uids = client.client.search(['UID', search_crit])
                
                # Filter out those <= last_uid just in case (server logic)
                real_new_uids = [u for u in new_uids if u > last_uid]
                
                if real_new_uids:
                    logger.info(f"Found {len(real_new_uids)} new emails for {email_addr}")
                    self.last_uids[email_addr] = max(real_new_uids)
                    
                    # Fetch details for notification
                    # We might limit to top 3 to avoid spamming
                    latest_uids = sorted(real_new_uids)[-3:]
                    
                    # We need fetch_emails equivalent but for specific UIDs
                    # imap_client doesn't have fetch_by_uids exposed nicely returning a list of dicts
                    # We can use fetch_emails logic or just raw client fetch
                    
                    response = client.client.fetch(latest_uids, ['ENVELOPE', 'FLAGS'])
                    for uid, data in response.items():
                        envelope = data[b'ENVELOPE']
                        subject = client._decode_str(envelope.subject)
                        sender = client._format_address(envelope.from_)
                        date = envelope.date
                        message_id = client._decode_str(envelope.message_id)
                        in_reply_to = client._decode_str(envelope.in_reply_to)
                        flags = [f.decode() if isinstance(f, bytes) else f for f in data.get(b'FLAGS', [])]

                        # Cache to DB
                        # We need account_id and folder_id (INBOX)
                        from ..database.db_manager import db_manager
                        account_id = db_manager.get_account_id(email_addr)
                        # Ensure INBOX folder exists
                        folder_id = db_manager.get_folder_id(account_id, "INBOX")
                        if not folder_id:
                            folder_id = db_manager.upsert_folder(account_id, "INBOX")
                            
                        db_manager.upsert_email(
                            account_id, folder_id, uid,
                            subject=subject,
                            sender=sender,
                            date=date,
                            flags=flags,
                            message_id=message_id,
                            in_reply_to=in_reply_to,
                            references=""
                        )

                        # Trigger Notification
                        notification_manager.show_toast(
                            title=f"New Email: {sender}",
                            message=subject,
                            on_click=None # Could eventually open the email
                        )
                        
                        # Play Sound
                        # Extract pure email for sender checking
                        sender_email = ""
                        if envelope.from_ and envelope.from_[0].mailbox and envelope.from_[0].host:
                            sender_email = f"{client._decode_str(envelope.from_[0].mailbox)}@{client._decode_str(envelope.from_[0].host)}"
                            
                        notification_manager.play_sound(category='INBOX', sender=sender_email, account_email=email_addr)

                client.logout()

            except Exception as e:
                logger.error(f"Error polling {email_addr}: {e}")
