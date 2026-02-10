
import wx
import logging
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleListCtrl
from ...utils.progress import AudibleProgress
from ...core.event_bus import EventBus, Events
from ...core.email_repository import EmailRepository
from ...core.shortcut_manager import shortcut_manager

logger = logging.getLogger(__name__)

class EmailListPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.threads = [] # Store thread root objects
        self.current_view_emails = [] # Emails currently displayed (flat list)
        self.current_by_uid = {}
        self.current_account = None
        self.current_folder = None
        self.repository = None
        self._load_token = 0
        self._load_progress = None
        
        # Threading state
        self.view_mode = "threads" # "threads" or "conversation"
        self.current_thread_root = None # The root of conversation being viewed
        
        # Pagination state
        self.limit = 100
        self.offset = 0
        
        self.init_ui()
        
        # Subscribe to folder updates
        EventBus.subscribe(Events.FOLDER_UPDATED, self.on_folder_selected)

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(self, label="Emails")
        sizer.Add(label, 0, wx.ALL, 5)

        self.list = AccessibleListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.init_accessible("Email list", "Use Up and Down arrows to navigate. Press Enter or Tab to read.")
        self.list.InsertColumn(0, "Sender", width=200)
        self.list.InsertColumn(1, "Subject", width=400)
        self.list.InsertColumn(2, "Date", width=150)
        self.list.InsertColumn(3, "Status", width=80)
        
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection_changed)
        self.list.Bind(wx.EVT_SET_FOCUS, self.on_focus)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

    def on_folder_selected(self, data):
        """
        Called when a folder is selected.
        """
        email_account = data.get('email')
        folder_name = data.get('name')
        
        if not email_account or not folder_name:
            return

        self.current_account = email_account
        self.current_folder = folder_name
        self.view_mode = "threads"
        self.current_thread_root = None
        self.offset = 0 # Reset offset
        
        speaker.speak(f"Loading emails from {folder_name}...")
        
        try:
            if not self.repository or self.repository.email != email_account:
                self.repository = EmailRepository(email_account)

            self.load_emails()
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            speaker.speak("Failed to load emails.")

    def load_emails(self):
        if not self.repository: return
        self._load_token += 1
        token = self._load_token

        # Load cached threads immediately for responsiveness
        cached = []
        try:
            cached = self.repository.get_cached_threads(self.current_folder, limit=self.limit, offset=self.offset)
        except Exception as e:
            logger.warning(f"Failed to load cached threads: {e}")
        if cached:
            self.threads = cached
            self.current_view_emails = self.threads
            self.refresh_list()
            speaker.speak("Loaded cached emails. Updating from server...")

        if self._load_progress:
            try:
                self._load_progress.stop()
            except Exception:
                pass
            self._load_progress = None

        self._load_progress = AudibleProgress("Loading emails, please wait", interval=6)
        self._load_progress.start()

        import threading
        threading.Thread(target=self._load_emails_worker, args=(token,), daemon=True).start()

    def _load_emails_worker(self, token: int):
        error = None
        raw_threads = []
        moved_count = 0
        try:
            # Load rules manager
            from ...core.rule_manager import RuleManager
            rule_manager = RuleManager()

            raw_threads = self.repository.fetch_threads(self.current_folder, limit=self.limit, offset=self.offset)

            # Apply rules to all folders/pages (if any)
            emails_to_move = [] # list of (uid, target_folder, email_obj, exclusive)

            def check_and_mark(email_obj):
                action = rule_manager.apply_rules(email_obj)
                if action and "move_to" in action:
                    target = action["move_to"]
                    if target and self.current_folder and target.lower() != self.current_folder.lower():
                        exclusive = bool(action.get("exclusive", True))
                        return (email_obj["uid"], target, email_obj, exclusive)
                return None

            for thread in raw_threads:
                # Check root
                res = check_and_mark(thread)
                if res:
                    emails_to_move.append(res)
                
                # Check children
                for child in thread.get("children", []):
                    res = check_and_mark(child)
                    if res:
                         emails_to_move.append(res)

            # Execute moves
            if emails_to_move:
                from collections import defaultdict
                moves_by_folder = defaultdict(list)
                
                for uid, target, obj, exclusive in emails_to_move:
                    moves_by_folder[target].append((uid, exclusive))
                    
                for target, items in moves_by_folder.items():
                    move_uids = [uid for uid, exclusive in items if exclusive]
                    copy_uids = [uid for uid, exclusive in items if not exclusive]
                    if move_uids and self.repository.move_emails(move_uids, target):
                        moved_count += len(move_uids)
                    if copy_uids and self.repository.copy_emails(copy_uids, target):
                        moved_count += len(copy_uids)
                        
                if moved_count > 0:
                    # Reload to reflect changes
                    raw_threads = self.repository.fetch_threads(self.current_folder, limit=self.limit, offset=self.offset)

        except Exception as e:
            error = e

        wx.CallAfter(self._finish_load_emails, token, raw_threads, moved_count, error)

    def _finish_load_emails(self, token: int, raw_threads, moved_count: int, error: Exception):
        if token != self._load_token:
            return

        if self._load_progress:
            try:
                self._load_progress.stop()
            except Exception:
                pass
            self._load_progress = None

        if error:
            logger.error(f"Failed to fetch emails: {error}")
            speaker.speak("Failed to load emails.")
            return

        if moved_count > 0:
            speaker.speak(f"Moved {moved_count} emails based on rules.")

        self.threads = raw_threads
        self.current_view_emails = self.threads # Initially show thread roots
        self.refresh_list()
        
        count = len(self.threads)
        if count > 0:
            msg = f"Loaded {count} conversations. Page {self.offset // self.limit + 1}."
        else:
            msg = "No emails found."
            
        speaker.speak(msg)
        
    def on_next_page(self):
        if not self.current_folder: return
        if len(self.threads) < self.limit and self.offset > 0:
             speaker.speak("No more emails.")
             return

        self.offset += self.limit
        speaker.speak("Loading next page...")
        self.load_emails()

    def on_prev_page(self):
        if self.offset == 0:
            speaker.speak("Already on first page.")
            return
            
        self.offset = max(0, self.offset - self.limit)
        speaker.speak("Loading previous page...")
        self.load_emails()

    def refresh_list(self):
        self.list.DeleteAllItems()
        self.current_by_uid = {}
        for idx, email in enumerate(self.current_view_emails):
            sender = email.get("sender", "Unknown")
            subject = email.get("subject", "No Subject")
            date = str(email.get("date", ""))
            flags = email.get("flags", [])
            is_read = "\\Seen" in flags
            status = "Read" if is_read else "Unread"
            uid = email.get("uid")
            
            # Add visual indicator for threads
            children = email.get("children", [])
            if self.view_mode == "threads" and children:
                subject = f"[+] {subject} ({len(children)+1})"
            
            self.list.InsertItem(idx, sender)
            self.list.SetItem(idx, 1, subject)
            self.list.SetItem(idx, 2, date)
            self.list.SetItem(idx, 3, status)
            if isinstance(uid, int):
                self.list.SetItemData(idx, uid)
                self.current_by_uid[uid] = email
            else:
                self.list.SetItemData(idx, idx)
    
        if self.current_view_emails:
            self.list.Select(0)
            self.list.Focus(0)

    def on_selection_changed(self, event):
        self._process_selection(event.GetIndex())

    def _process_selection(self, index):
        if 0 <= index < len(self.current_view_emails):
            email = self.current_view_emails[index]
            
            # Announce slightly differently if it's a thread root
            children = email.get("children", [])
            is_thread = self.view_mode == "threads" and children
            
            subject = email.get('subject', 'No Subject')
            flags = email.get("flags", [])
            is_read = "\\Seen" in flags
            status = "Read" if is_read else "Unread"
            if is_thread:
                expand_hint = shortcut_manager.get_shortcut("expand_thread")
                hint_text = f"Press {expand_hint} to expand." if expand_hint else "Press the expand shortcut to expand."
                speaker.speak(f"Conversation: {subject}, {len(children)+1} messages. From {email.get('sender')}. {status}. {hint_text}")
            else:
                speaker.speak(f"Email from {email.get('sender')}, {subject}. {status}. Press Tab to read content.")
            
            # Publish event
            EventBus.publish(Events.EMAIL_SELECTED, email)

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        idx = self.list.GetFocusedItem()
        if idx == -1:
            idx = self.list.GetFirstSelected()
        
        if keycode == wx.WXK_RETURN or keycode == wx.WXK_TAB or shortcut_manager.matches_event("open_email", event):
            if idx != -1:
                self._open_selected(idx)
                return

        elif shortcut_manager.matches_event("next_page", event) or keycode == wx.WXK_PAGEDOWN:
            self.on_next_page()
            return

        elif shortcut_manager.matches_event("prev_page", event) or keycode == wx.WXK_PAGEUP:
            self.on_prev_page()
            return

        elif shortcut_manager.matches_event("expand_thread", event):
            if self.view_mode == "threads" and idx != -1:
                email = self.current_view_emails[idx]
                children = email.get("children", [])
                if children:
                    self.enter_thread_view(email)
                else:
                    speaker.speak("No replies in this conversation.")
            return
        elif keycode == wx.WXK_RIGHT and not (event.ControlDown() or event.AltDown() or event.ShiftDown()):
            if self.view_mode == "threads" and idx != -1:
                email = self.current_view_emails[idx]
                children = email.get("children", [])
                if children:
                    self.enter_thread_view(email)
                else:
                    speaker.speak("No replies in this conversation.")
            return

        elif shortcut_manager.matches_event("collapse_thread", event):
            if self.view_mode == "conversation":
                self.exit_thread_view()
            return
        elif keycode == wx.WXK_LEFT and not (event.ControlDown() or event.AltDown() or event.ShiftDown()):
            if self.view_mode == "conversation":
                self.exit_thread_view()
            return

        elif shortcut_manager.matches_event("delete", event):
            self.delete_selected()
            return

        elif shortcut_manager.matches_event("archive", event):
            self.archive_selected()
            return
            
        else:
            event.Skip()

    def _open_selected(self, idx):
        if idx == -1:
            return

        email_data = None
        item_data = self.list.GetItemData(idx)
        if isinstance(item_data, int) and item_data in self.current_by_uid:
            email_data = self.current_by_uid[item_data]
        elif 0 <= idx < len(self.current_view_emails):
            email_data = self.current_view_emails[idx]

        if not email_data:
            speaker.speak("Unable to open selected message")
            return

        email_data['folder'] = self.current_folder
        email_data['account'] = self.current_account

        speaker.speak("Opening email content")
        EventBus.publish(Events.EMAIL_OPENED, email_data)
        self._mark_read_async(email_data)

    def _mark_read_async(self, email_data):
        if not self.repository:
            return
        uid = email_data.get("uid")
        folder = email_data.get("folder") or self.current_folder
        if not isinstance(uid, int):
            return
        flags = email_data.get("flags", [])
        if "\\Seen" in flags:
            return

        import threading
        def worker():
            try:
                if self.repository.add_flags([uid], ["\\Seen"], folder_name=folder):
                    wx.CallAfter(self._apply_read_flag, uid)
            except Exception as e:
                logger.warning(f"Failed to mark read: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _apply_read_flag(self, uid: int):
        updated = False
        for email_obj in self.current_view_emails:
            if email_obj.get("uid") == uid:
                flags = email_obj.get("flags", [])
                if "\\Seen" not in flags:
                    flags.append("\\Seen")
                email_obj["flags"] = flags
                updated = True
                break
        if updated:
            self.refresh_list()

    def _find_target_folder(self, candidates):
        if not self.repository: return None
        # Resolve a candidate against the server folder list.
        if self.repository.imap_client:
            folders = self.repository.imap_client.list_folders()
            folder_names = [f['name'] for f in folders]
            
            for candidate in candidates:
                 if candidate in folder_names:
                     return candidate
                 
            for candidate in candidates:
                 for real_name in folder_names:
                     if candidate.lower() == real_name.lower():
                         return real_name
        return None

    def delete_selected(self):
        idx = self.list.GetFirstSelected()
        if idx == -1: return

        if idx < len(self.current_view_emails):
            email_obj = self.current_view_emails[idx]
            uid = email_obj.get("uid")
            
            # Confirm
            if wx.MessageBox("Delete this conversation/email?", "Confirm Delete", wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
                return

            speaker.speak("Deleting...")
            
            # Find Trash
            trash_candidates = ["Trash", "Bin", "Deleted Items", "Deleted", "[Gmail]/Trash"]
            target = self._find_target_folder(trash_candidates)
            
            success = False
            if target:
                success = self.repository.move_emails([uid], target)
            else:
                success = self.repository.add_flags([uid], ["\\Deleted"])
            
            if success:
                speaker.speak("Deleted.")
                # Remove from list
                self.current_view_emails.pop(idx)
                if self.view_mode == "threads":
                     if email_obj in self.threads:
                         self.threads.remove(email_obj)
                self.refresh_list()
                
                new_count = self.list.GetItemCount()
                if new_count > 0:
                    new_idx = min(idx, new_count - 1)
                    self.list.Select(new_idx)
                    self.list.Focus(new_idx)
            else:
                speaker.speak("Failed to delete.")

    def archive_selected(self):
        idx = self.list.GetFirstSelected()
        if idx == -1: return
        
        email_obj = self.current_view_emails[idx]
        uid = email_obj.get("uid")

        speaker.speak("Archiving...")
        
        # Find Archive
        archive_candidates = ["Archive", "Archives", "All Mail", "[Gmail]/All Mail"]
        target = self._find_target_folder(archive_candidates)
        
        if target:
            if self.repository.move_emails([uid], target):
                speaker.speak("Archived.")
                self.current_view_emails.pop(idx)
                if self.view_mode == "threads" and email_obj in self.threads:
                    self.threads.remove(email_obj)
                self.refresh_list()
                
                new_count = self.list.GetItemCount()
                if new_count > 0:
                    new_idx = min(idx, new_count - 1)
                    self.list.Select(new_idx)
                    self.list.Focus(new_idx)
            else:
                 speaker.speak("Failed to archive.")
        else:
            speaker.speak("Archive folder not found.")

    def enter_thread_view(self, thread_root):
        self.view_mode = "conversation"
        self.current_thread_root = thread_root
        conversation = [thread_root] + thread_root.get("children", [])
        self.current_view_emails = conversation
        self.refresh_list()
        speaker.speak(f"Expanded conversation. {len(conversation)} messages.")

    def exit_thread_view(self):
        self.view_mode = "threads"
        self.current_view_emails = self.threads
        self.refresh_list()
        try:
            idx = self.threads.index(self.current_thread_root)
            self.list.Select(idx)
            self.list.Focus(idx)
        except:
            self.list.Select(0)
            
        self.current_thread_root = None
        speaker.speak("Back to conversation list.")

    def on_focus(self, event):
        mode = "Conversation list" if self.view_mode == "threads" else "Thread view"
        speaker.speak(mode)
        event.Skip()
