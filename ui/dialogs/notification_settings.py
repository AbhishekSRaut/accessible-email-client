import wx
from ...utils.accessible_widgets import AccessibleListBox, AccessibleButton, AccessibleTextCtrl, AccessibleChoice
from ...utils.accessibility import speaker
from ...core.notification_manager import notification_manager


class NotificationSettingsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Notification Sounds", size=(650, 520))
        self.entries = []
        self.edit_index = None
        self.init_ui()
        self.load_entries()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        main = wx.BoxSizer(wx.VERTICAL)

        self.list = AccessibleListBox(panel, choices=[])
        self.list.init_accessible("Sound rules list", "Select a rule to edit or delete")
        self.list.Bind(wx.EVT_LISTBOX, self.on_select_entry)
        main.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        form_box = wx.StaticBox(panel, label="Add or Edit Rule")
        form = wx.StaticBoxSizer(form_box, wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=5, cols=2, vgap=10, hgap=10)

        # Scope
        grid.Add(wx.StaticText(panel, label="Scope:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.scope_choice = AccessibleChoice(panel, choices=["Global", "Account"])
        self.scope_choice.SetSelection(0)
        self.scope_choice.init_accessible("Scope", "Global or account specific")
        self.scope_choice.Bind(wx.EVT_CHOICE, self.on_scope_changed)
        grid.Add(self.scope_choice, 1, wx.EXPAND)

        # Account
        grid.Add(wx.StaticText(panel, label="Account:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.account_input = AccessibleTextCtrl(panel, value="")
        self.account_input.init_accessible("Account email")
        grid.Add(self.account_input, 1, wx.EXPAND)

        # Type
        grid.Add(wx.StaticText(panel, label="Type:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.type_choice = AccessibleChoice(panel, choices=["Default", "Folder", "Sender"])
        self.type_choice.SetSelection(0)
        self.type_choice.init_accessible("Rule type")
        self.type_choice.Bind(wx.EVT_CHOICE, self.on_type_changed)
        grid.Add(self.type_choice, 1, wx.EXPAND)

        # Target (folder or sender)
        self.target_label = wx.StaticText(panel, label="Folder:")
        grid.Add(self.target_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.target_input = AccessibleTextCtrl(panel, value="")
        self.target_input.init_accessible("Target value")
        grid.Add(self.target_input, 1, wx.EXPAND)

        # Sound
        grid.Add(wx.StaticText(panel, label="Sound (alias or .wav path):"), 0, wx.ALIGN_CENTER_VERTICAL)
        sound_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sound_input = AccessibleTextCtrl(panel, value="")
        self.sound_input.init_accessible("Sound value")
        browse_btn = AccessibleButton(panel, label="Browse...")
        browse_btn.init_accessible("Browse for sound file", announce=False)
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        sound_sizer.Add(self.sound_input, 1, wx.RIGHT, 5)
        sound_sizer.Add(browse_btn, 0)
        grid.Add(sound_sizer, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        form.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = AccessibleButton(panel, label="Add Rule")
        self.save_btn.init_accessible("Add or update rule button", announce=False)
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        self.delete_btn = AccessibleButton(panel, label="Delete Selected")
        self.delete_btn.init_accessible("Delete selected rule button", announce=False)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        close_btn = AccessibleButton(panel, label="Close")
        close_btn.init_accessible("Close button", announce=False)
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        btns.Add(self.save_btn, 0, wx.RIGHT, 10)
        btns.Add(self.delete_btn, 0, wx.RIGHT, 10)
        btns.Add(close_btn, 0)

        form.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        main.Add(form, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(main)
        self.on_scope_changed(None)
        self.on_type_changed(None)

    def load_entries(self):
        self.entries = self._prefs_to_entries(notification_manager.get_preferences())
        self.list.Clear()
        if not self.entries:
            self.list.Append("No notification sound rules")
            self.list.SetSelection(0)
            self.delete_btn.Disable()
            return
        for entry in self.entries:
            self.list.Append(self._render_entry(entry))
        self.list.SetSelection(0)
        self.delete_btn.Enable()

    def _prefs_to_entries(self, prefs):
        entries = []
        if not prefs:
            return entries

        # Global default
        if prefs.get("default"):
            entries.append({"scope": "global", "type": "default", "sound": prefs["default"]})

        for folder, sound in (prefs.get("folders") or {}).items():
            entries.append({"scope": "global", "type": "folder", "key": folder, "sound": sound})

        for sender, sound in (prefs.get("senders") or {}).items():
            entries.append({"scope": "global", "type": "sender", "key": sender, "sound": sound})

        for account, acc in (prefs.get("accounts") or {}).items():
            if acc.get("default"):
                entries.append({"scope": "account", "account": account, "type": "default", "sound": acc["default"]})
            for folder, sound in (acc.get("folders") or {}).items():
                entries.append({"scope": "account", "account": account, "type": "folder", "key": folder, "sound": sound})
            for sender, sound in (acc.get("senders") or {}).items():
                entries.append({"scope": "account", "account": account, "type": "sender", "key": sender, "sound": sound})

        return entries

    def _render_entry(self, entry):
        scope = "Global" if entry.get("scope") == "global" else f"Account {entry.get('account')}"
        typ = entry.get("type")
        if typ == "default":
            return f"{scope}: Default -> {entry.get('sound')}"
        if typ == "folder":
            return f"{scope}: Folder '{entry.get('key')}' -> {entry.get('sound')}"
        if typ == "sender":
            return f"{scope}: Sender '{entry.get('key')}' -> {entry.get('sound')}"
        return f"{scope}: Unknown -> {entry.get('sound')}"

    def on_scope_changed(self, event):
        is_account = self.scope_choice.GetStringSelection() == "Account"
        self.account_input.Enable(is_account)
        if not is_account:
            self.account_input.SetValue("")

    def on_type_changed(self, event):
        typ = self.type_choice.GetStringSelection()
        if typ == "Folder":
            self.target_label.SetLabel("Folder:")
            self.target_input.Enable(True)
        elif typ == "Sender":
            self.target_label.SetLabel("Sender Email:")
            self.target_input.Enable(True)
        else:
            self.target_label.SetLabel("Target:")
            self.target_input.SetValue("")
            self.target_input.Enable(False)

    def on_select_entry(self, event):
        idx = self.list.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self.entries):
            return
        entry = self.entries[idx]
        self.edit_index = idx
        self.save_btn.SetLabel("Update Rule")

        scope = entry.get("scope")
        self.scope_choice.SetSelection(0 if scope == "global" else 1)
        self.on_scope_changed(None)

        if scope == "account":
            self.account_input.SetValue(entry.get("account", ""))

        typ = entry.get("type")
        if typ == "default":
            self.type_choice.SetSelection(0)
        elif typ == "folder":
            self.type_choice.SetSelection(1)
        else:
            self.type_choice.SetSelection(2)
        self.on_type_changed(None)

        self.target_input.SetValue(entry.get("key", "") if typ in ["folder", "sender"] else "")
        self.sound_input.SetValue(entry.get("sound", ""))

    def _build_entry_from_form(self):
        scope = self.scope_choice.GetStringSelection().lower()
        typ = self.type_choice.GetStringSelection().lower()
        sound = self.sound_input.GetValue().strip()

        if not sound:
            speaker.speak("Sound is required")
            return None

        entry = {"scope": scope, "type": typ, "sound": sound}

        if scope == "account":
            account = self.account_input.GetValue().strip().lower()
            if not account:
                speaker.speak("Account email is required")
                return None
            entry["account"] = account

        if typ in ["folder", "sender"]:
            key = self.target_input.GetValue().strip().lower()
            if not key:
                speaker.speak("Folder or sender is required")
                return None
            entry["key"] = key

        return entry

    def on_save(self, event):
        entry = self._build_entry_from_form()
        if not entry:
            return

        prefs = notification_manager.get_preferences()
        prefs = self._apply_entry_to_prefs(prefs, entry)
        notification_manager.set_preferences(prefs)
        speaker.speak("Notification sound rule saved")
        self.edit_index = None
        self.save_btn.SetLabel("Add Rule")
        self.load_entries()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def on_delete(self, event):
        idx = self.list.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self.entries):
            return
        entry = self.entries[idx]
        prefs = notification_manager.get_preferences()
        prefs = self._remove_entry_from_prefs(prefs, entry)
        notification_manager.set_preferences(prefs)
        speaker.speak("Notification sound rule deleted")
        self.edit_index = None
        self.save_btn.SetLabel("Add Rule")
        self.load_entries()

    def _apply_entry_to_prefs(self, prefs, entry):
        if not prefs:
            prefs = {"default": "SystemAsterisk", "folders": {}, "senders": {}, "accounts": {}}

        if entry["scope"] == "global":
            target = prefs
        else:
            acc_key = entry["account"]
            accounts = prefs.setdefault("accounts", {})
            target = accounts.setdefault(acc_key, {"default": None, "folders": {}, "senders": {}})

        if entry["type"] == "default":
            target["default"] = entry["sound"]
        elif entry["type"] == "folder":
            folders = target.setdefault("folders", {})
            folders[entry["key"]] = entry["sound"]
        elif entry["type"] == "sender":
            senders = target.setdefault("senders", {})
            senders[entry["key"]] = entry["sound"]

        return prefs

    def _remove_entry_from_prefs(self, prefs, entry):
        if not prefs:
            return prefs

        if entry["scope"] == "global":
            target = prefs
        else:
            target = (prefs.get("accounts") or {}).get(entry.get("account"), {})

        if entry["type"] == "default":
            if "default" in target:
                target["default"] = None
        elif entry["type"] == "folder":
            folders = target.get("folders") or {}
            folders.pop(entry.get("key"), None)
        elif entry["type"] == "sender":
            senders = target.get("senders") or {}
            senders.pop(entry.get("key"), None)

        return prefs

    def on_browse(self, event):
        with wx.FileDialog(self, "Select Sound File", wildcard="WAV files (*.wav)|*.wav|All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            self.sound_input.SetValue(dlg.GetPath())
