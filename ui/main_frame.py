
import wx
import logging
from .panels.folder_list import FolderListPanel
from .panels.email_list import EmailListPanel
from .panels.message_viewer import MessageViewerPanel
from ..utils.accessibility import speaker
from ..core.notification_manager import notification_manager
from ..core.email_poller import EmailPoller
from .tray_icon import TrayIconManager
from ..utils.single_instance import instance_guard
import threading
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Accessible Email Client", size=(1024, 768))
        self._hotkey_ids = {}
        self.init_ui()
        self.CreateStatusBar()
        self.SetStatusText("Ready")
        self.Center()
        self.Show()
        speaker.speak("Accessible Email Client Ready")
        
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_HOTKEY, self.on_hotkey)
        self._register_hotkeys()

        # Initialize Notification System
        self.email_poller = EmailPoller(interval=60)
        self.email_poller.start()

        self.tray_icon = TrayIconManager(
            on_open=lambda: wx.CallAfter(self.restore_from_tray),
            on_exit=lambda: wx.CallAfter(self.force_exit)
        )
        self.tray_icon.start()

        # Start single-instance listener so new instances can signal us to restore
        instance_guard.start_listener(lambda: wx.CallAfter(self.restore_from_tray))

    def init_ui(self):
        # Create Menu Bar
        menubar = wx.MenuBar()
        
        from ..core.shortcut_manager import shortcut_manager
        
        # Register Actions
        shortcut_manager.register("compose", "Compose Email", "Ctrl+N", self.on_compose)
        shortcut_manager.register("reply", "Reply", "Alt+Shift+R", self.on_reply)
        shortcut_manager.register("reply_all", "Reply All", "Alt+Shift+A", self.on_reply_all)
        shortcut_manager.register("forward", "Forward", "Alt+Shift+F", self.on_forward)
        shortcut_manager.register("exit", "Exit Application", "Ctrl+Q", self.on_exit)
        shortcut_manager.register("add_account", "Add Account", "Ctrl+Shift+A", self.on_add_account)
        shortcut_manager.register("create_folder", "Create Folder", "Ctrl+Shift+N", self.on_create_folder)
        shortcut_manager.register("silent_mode", "Toggle Silent Mode", "Ctrl+S", self.on_toggle_silent_mode)
        shortcut_manager.register("shortcuts_dialog", "Manage Shortcuts", "Ctrl+K", self.on_show_shortcuts)
        
        # New Actions
        shortcut_manager.register("delete", "Delete Selected", "Delete", self.on_delete)
        shortcut_manager.register("archive", "Archive Selected", "Ctrl+Alt+A", self.on_archive, global_accel=False)
        shortcut_manager.register("refresh_list", "Refresh List", "F5", self.on_refresh_list)
        shortcut_manager.register("next_page", "Next Page", "Ctrl+Right", self.on_next_page)
        shortcut_manager.register("prev_page", "Previous Page", "Ctrl+Left", self.on_prev_page)
        # Local actions
        shortcut_manager.register("open_email", "Open Email", "Return", None, global_accel=False)
        shortcut_manager.register("expand_thread", "Expand Thread", "Right", None, global_accel=False)
        shortcut_manager.register("collapse_thread", "Collapse Thread", "Left", None, global_accel=False)
        shortcut_manager.register("focus_actions", "Focus Actions Panel", "F6", None, global_accel=False)
        shortcut_manager.register("focus_message_list", "Focus Message List", "Alt+Shift+L", self.on_focus_message_list, global_accel=True)

        # Initialize Menu and Accelerators
        self.refresh_shortcuts()

        # Layout
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Main Splitter (Left: Folders, Right: Emails+Viewer)
        self.splitter = wx.SplitterWindow(panel, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        
        # Left Panel (Folder List)
        self.folder_panel = FolderListPanel(self.splitter)
        
        # Right Splitter (Top: Email List, Bottom: Viewer)
        self.right_splitter = wx.SplitterWindow(self.splitter, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        
        self.email_list_panel = EmailListPanel(self.right_splitter)
        self.message_viewer_panel = MessageViewerPanel(self.right_splitter)
        
        # Set Splitter Defaults
        self.right_splitter.SplitHorizontally(self.email_list_panel, self.message_viewer_panel)
        self.right_splitter.SetSashGravity(0.5)
        
        self.splitter.SplitVertically(self.folder_panel, self.right_splitter)
        self.splitter.SetSashGravity(0.2)
        
        sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(sizer)

    def on_manage_rules(self, event):
        # Gather folder list for the rules dialog.
        folders = []
        # Use IMAP for a complete list.
        account = self.email_list_panel.current_account
        if not account:
            # try finding from folder panel selection
            account = self.folder_panel.get_selected_account()
            
        if not account:
            speaker.speak("Please select an account first")
            wx.MessageBox("Please select an account or folder first.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Fetch folders for this account
        from ..core.imap_client import IMAPClient
        client = IMAPClient(account)
        try:
            folder_list = client.list_folders()
            folders = [f['name'] for f in folder_list]
        except:
             speaker.speak("Failed to list folders")
             return

        from .dialogs.rules_dialog import RulesDialog
        dlg = RulesDialog(self, folders=folders, account_email=account)
        dlg.ShowModal()
        dlg.Destroy()


    def on_exit(self, event):
        self.force_exit()

    def on_toggle_silent_mode(self, event):
        is_silent = not notification_manager.silent_mode
        notification_manager.set_silent_mode(is_silent)
        status = "enabled" if is_silent else "disabled"
        speaker.speak(f"Silent mode {status}")
        logger.info(f"Silent mode {status}")

    def on_about(self, event):
        wx.MessageBox("Accessible Email Client\nVersion 1.2\n\nDesigned for accessibility.", "About", wx.OK | wx.ICON_INFORMATION)

    def on_contact_developer(self, event):
        accounts = self._check_account_config()
        if not accounts:
            return
        from .dialogs.compose import ComposeDialog
        current_account = self.email_list_panel.current_account or accounts[0]['email']
        dialog = ComposeDialog(self, account_email=current_account, initial_to="raut.abhishek@zohomail.in", compose_mode="new")
        dialog.ShowModal()
        dialog.Destroy()

    def on_open_github(self, event):
        webbrowser.open("https://github.com/abhisheksraut")

    def on_open_help_doc(self, event):
        doc_path = Path(__file__).resolve().parents[1] / "doc" / "README.html"
        if doc_path.exists():
            webbrowser.open(doc_path.as_uri())
        else:
            wx.MessageBox("Help file not found.", "Error", wx.OK | wx.ICON_ERROR)


    def on_close(self, event):
        if event.CanVeto():
            self.Hide()
            self.tray_icon.icon.notify("Accessible Email Client is running in background.", "Application Minimized")
            event.Veto()
        else:
            self.force_exit()

    def restore_from_tray(self):
        self.Show()
        self.Raise()

    def force_exit(self):
        if hasattr(self, 'email_poller'):
            self.email_poller.stop()
        
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self._unregister_hotkeys()
        instance_guard.cleanup()
        self.Destroy()


    def on_create_folder(self, event):
        # Determine account
        account_email = self.folder_panel.get_selected_account()
        if not account_email:
            account_email = self.email_list_panel.current_account
            
        if not account_email:
             # Try first available account
             from ..core.account_manager import AccountManager
             accounts = AccountManager().get_accounts()
             if accounts:
                 account_email = accounts[0]['email']
             else:
                 wx.MessageBox("No accounts configured.", "Error", wx.OK | wx.ICON_ERROR)
                 return
        
        input_dlg = wx.TextEntryDialog(self, "Enter new folder name:", "Create Folder")
        if input_dlg.ShowModal() == wx.ID_OK:
            folder_name = input_dlg.GetValue()
            if folder_name:
                from ..core.imap_client import IMAPClient
                # We need to reuse the client if possible to avoid reconnect
                # But creating a new one is safe enough
                client = IMAPClient(account_email)
                if client.create_folder(folder_name):
                    speaker.speak(f"Folder {folder_name} created.")
                    wx.MessageBox(f"Folder '{folder_name}' created successfully.", "Success", wx.OK | wx.ICON_INFORMATION)
                    self.folder_panel.refresh_folders(account_email)
                else:
                    speaker.speak("Failed to create folder.")
                    wx.MessageBox(f"Failed to create folder '{folder_name}'.", "Error", wx.OK | wx.ICON_ERROR)
        input_dlg.Destroy()

    def _get_selected_email(self):
        # Helper to get selected email from EmailListPanel or Viewer
        # EmailListPanel has the selection state
        idx = self.email_list_panel.list.GetFirstSelected()
        if idx != -1 and idx < len(self.email_list_panel.current_view_emails):
            return self.email_list_panel.current_view_emails[idx]
        return None

    def _check_account_config(self):
        from ..core.account_manager import AccountManager
        am = AccountManager()
        accounts = am.get_accounts()
        if not accounts:
            dlg = wx.MessageDialog(self, "No email accounts configured. Would you like to add one now?", 
                                   "No Accounts", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                self.on_add_account(None)
            dlg.Destroy()
            return None
        return accounts

    def on_compose(self, event):
        accounts = self._check_account_config()
        if not accounts: return

        from .dialogs.compose import ComposeDialog
        current_account = self.email_list_panel.current_account
        if not current_account and accounts:
            current_account = accounts[0]['email']
            
        dialog = ComposeDialog(self, account_email=current_account, compose_mode="new")
        dialog.ShowModal()
        dialog.Destroy()

    def on_reply(self, event):
        accounts = self._check_account_config()
        if not accounts: return
        
        email = self._get_selected_email()
        if not email:
            speaker.speak("No email selected to reply to")
            return
            
        sender = email.get("sender", "")
        
        subject = email.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = "Re: " + subject
            
        # Quote headers if body isn't available.
        body = email.get("body_text", "")
        if not body:
             body = "\n\n--- Original Message ---\n"
             body += f"From: {sender}\nDate: {email.get('date')}\nSubject: {email.get('subject')}\n"
        else:
            body = f"\n\n--- Original Message ---\nFrom: {sender}\nDate: {email.get('date')}\nSubject: {email.get('subject')}\n\n{body}"

        from .dialogs.compose import ComposeDialog
        current_account = self.email_list_panel.current_account or accounts[0]['email']
        
        dialog = ComposeDialog(self, account_email=current_account, 
                               initial_to=sender, initial_subject=subject, initial_body=body, compose_mode="reply")
        dialog.ShowModal()
        dialog.Destroy()

    def on_reply_all(self, event):
        if self.message_viewer_panel:
            self.message_viewer_panel.on_reply_all(None)

    def on_forward(self, event):
        accounts = self._check_account_config()
        if not accounts: return
        
        email = self._get_selected_email()
        if not email:
            speaker.speak("No email selected to forward")
            return
            
        subject = email.get("subject", "")
        if not subject.lower().startswith("fwd:"):
            subject = "Fwd: " + subject
            
        sender = email.get("sender", "")
        body = "\n\n--- Forwarded Message ---\n"
        body += f"From: {sender}\nDate: {email.get('date')}\nSubject: {email.get('subject')}\n"
        # Body content may not be cached yet.
        
        from .dialogs.compose import ComposeDialog
        current_account = self.email_list_panel.current_account or accounts[0]['email']
        
        dialog = ComposeDialog(self, account_email=current_account, 
                               initial_subject=subject, initial_body=body, compose_mode="forward")
        dialog.ShowModal()
        dialog.Destroy()

    def on_add_account(self, event):
        from .dialogs.add_account import AddAccountDialog
        dialog = AddAccountDialog(self)
        dialog.ShowModal()
        dialog.Destroy()

    def on_char_hook(self, event):
        keycode = event.GetKeyCode()
        from ..core.shortcut_manager import shortcut_manager
        focused = wx.Window.FindFocus()
        webview = getattr(self.message_viewer_panel, "webview", None) if hasattr(self, "message_viewer_panel") else None
        if focused and webview and focused is webview:
            if keycode == wx.WXK_ESCAPE:
                self.on_focus_message_list(None)
                return
            if shortcut_manager.matches_event("focus_message_list", event):
                self.on_focus_message_list(None)
                return
            if shortcut_manager.matches_event("reply", event):
                self.on_reply(None)
                return
            if shortcut_manager.matches_event("forward", event):
                self.on_forward(None)
                return
            if shortcut_manager.matches_event("delete", event):
                self.on_delete(None)
                return
            if shortcut_manager.matches_event("archive", event):
                self.on_archive(None)
                return
            if shortcut_manager.matches_event("focus_actions", event):
                if self.message_viewer_panel:
                    self.message_viewer_panel.reply_btn.SetFocus()
                    speaker.speak("Actions")
                return
        if keycode == wx.WXK_TAB:
            focused = wx.Window.FindFocus()
            if focused and self.message_viewer_panel and self.message_viewer_panel.webview:
                if focused is self.message_viewer_panel.webview:
                    if self.message_viewer_panel.handle_webview_tab(event):
                        return
        event.Skip()

    def _register_hotkeys(self):
        # System-level hotkeys to work even when WebView swallows keys
        hotkeys = {
            "focus_message_list": (wx.MOD_ALT | wx.MOD_SHIFT, ord("L")),
            "reply": (wx.MOD_ALT | wx.MOD_SHIFT, ord("R")),
            "reply_all": (wx.MOD_ALT | wx.MOD_SHIFT, ord("A")),
            "forward": (wx.MOD_ALT | wx.MOD_SHIFT, ord("F")),
        }
        base_id = wx.NewIdRef()
        i = 0
        for action_id, (mods, keycode) in hotkeys.items():
            hk_id = int(base_id) + i
            i += 1
            if self.RegisterHotKey(hk_id, mods, keycode):
                self._hotkey_ids[hk_id] = action_id
            else:
                logger.warning(f"Failed to register hotkey for {action_id}")

    def _unregister_hotkeys(self):
        for hk_id in list(self._hotkey_ids.keys()):
            try:
                self.UnregisterHotKey(hk_id)
            except Exception:
                pass
        self._hotkey_ids = {}

    def on_hotkey(self, event):
        if not self.IsActive():
            return
        action_id = self._hotkey_ids.get(event.GetId())
        if action_id == "focus_message_list":
            self.on_focus_message_list(None)
        elif action_id == "reply":
            self.on_reply(None)
        elif action_id == "reply_all":
            self.on_reply_all(None)
        elif action_id == "forward":
            self.on_forward(None)

    def on_delete(self, event):
        if self.email_list_panel:
            self.email_list_panel.delete_selected()
            
    def on_archive(self, event):
        if self.email_list_panel:
            self.email_list_panel.archive_selected()

    def on_refresh_list(self, event):
        if self.email_list_panel:
            self.email_list_panel.load_emails()
            speaker.speak("Refreshing email list...")

    def on_next_page(self, event):
        if self.email_list_panel:
            self.email_list_panel.on_next_page()
            
    def on_prev_page(self, event):
        if self.email_list_panel:
            self.email_list_panel.on_prev_page()

    def on_show_shortcuts(self, event):
        from .dialogs.shortcuts_dialog import ShortcutsDialog
        dlg = ShortcutsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
        self.refresh_shortcuts()

    def on_focus_message_list(self, event):
        if self.email_list_panel:
            self.email_list_panel.list.SetFocus()
            speaker.speak("Email list")

    def refresh_shortcuts(self):
        from ..core.shortcut_manager import shortcut_manager
        
        # Save state
        is_silent = notification_manager.silent_mode
        
        # Rebuild/Update Menu
        old_menubar = self.GetMenuBar()
        if old_menubar:
            self.SetMenuBar(None)
            old_menubar.Destroy()
            
        self.create_menu_bar()
        
        # Nothing to restore in the menu, settings live in dialog now.
        if hasattr(self, 'normalize_html_item'):
            try:
                self.normalize_html_item.Check(config.get_bool("normalize_html", True))
            except:
                pass
            
        # Rebuild Accelerator Table
        shortcut_manager.build_accelerator_table(self)
        if hasattr(self, "message_viewer_panel") and self.message_viewer_panel:
            try:
                self.message_viewer_panel.refresh_shortcuts()
            except Exception:
                pass

    def create_menu_bar(self):
        from ..core.shortcut_manager import shortcut_manager
        
        menubar = wx.MenuBar()
        
        # File Menu
        file_menu = wx.Menu()
        compose_item = file_menu.Append(wx.ID_ANY, f"Compose Email\t{shortcut_manager.get_shortcut('compose')}", "Compose a new email")
        reply_item = file_menu.Append(wx.ID_ANY, f"Reply\t{shortcut_manager.get_shortcut('reply')}", "Reply to sender")
        forward_item = file_menu.Append(wx.ID_ANY, f"Forward\t{shortcut_manager.get_shortcut('forward')}", "Forward email")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, f"Exit\t{shortcut_manager.get_shortcut('exit')}", "Exit the application")
        menubar.Append(file_menu, "&File")
        
        # Account Menu
        account_menu = wx.Menu()
        add_account_item = account_menu.Append(wx.ID_ANY, f"Add Account...\t{shortcut_manager.get_shortcut('add_account')}", "Add a new email account")
        manage_accounts_item = account_menu.Append(wx.ID_ANY, "Manage Accounts...", "Manage email accounts")
        menubar.Append(account_menu, "&Account")
        
        # Folder Menu
        folder_menu = wx.Menu()
        create_folder_item = folder_menu.Append(wx.ID_ANY, f"Create Folder...\t{shortcut_manager.get_shortcut('create_folder')}", "Create a new folder")
        manage_rules_item = folder_menu.Append(wx.ID_ANY, "Manage Rules...", "Manage smart folder rules")
        menubar.Append(folder_menu, "F&older")
        
        # Settings Menu (before Help)
        settings_menu = wx.Menu()
        settings_item = settings_menu.Append(wx.ID_ANY, "Settings...", "Open settings")
        menubar.Append(settings_menu, "&Settings")

        # Help Menu (last)
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "About", "About this application")
        contact_item = help_menu.Append(wx.ID_ANY, "Contact Developer (Email)", "Email the developer")
        github_item = help_menu.Append(wx.ID_ANY, "Open Developer GitHub", "Open developer GitHub profile")
        docs_item = help_menu.Append(wx.ID_ANY, "Open User Guide", "Open the user guide")
        menubar.Append(help_menu, "&Help")
        
        self.SetMenuBar(menubar)
        
        # Bind
        self.Bind(wx.EVT_MENU, self.on_compose, compose_item)
        self.Bind(wx.EVT_MENU, self.on_reply, reply_item)
        self.Bind(wx.EVT_MENU, self.on_forward, forward_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        self.Bind(wx.EVT_MENU, self.on_contact_developer, contact_item)
        self.Bind(wx.EVT_MENU, self.on_open_github, github_item)
        self.Bind(wx.EVT_MENU, self.on_open_help_doc, docs_item)
        self.Bind(wx.EVT_MENU, self.on_add_account, add_account_item)
        self.Bind(wx.EVT_MENU, self.on_manage_accounts, manage_accounts_item)
        self.Bind(wx.EVT_MENU, self.on_create_folder, create_folder_item)
        self.Bind(wx.EVT_MENU, self.on_manage_rules, manage_rules_item)
        self.Bind(wx.EVT_MENU, self.on_open_settings, settings_item)

    def on_add_account(self, event):
        from .dialogs.account_dialog import AccountDialog
        dlg = AccountDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            if self.folder_panel:
                self.folder_panel.load_accounts()
        dlg.Destroy()

    def on_manage_accounts(self, event):
        from .dialogs.manage_accounts import ManageAccountsDialog
        dlg = ManageAccountsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
        # Refresh folder list after managing
        if self.folder_panel:
            self.folder_panel.load_accounts()

    def on_manage_notifications(self, event):
        from .dialogs.notification_settings import NotificationSettingsDialog
        dlg = NotificationSettingsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_open_settings(self, event):
        from .dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
