import wx
from ...utils.accessible_widgets import AccessibleButton, AccessibleTextCtrl, AccessibleChoice
from ...utils.accessibility import speaker
from ...core.configuration import config


class SignatureSettingsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Signatures", size=(680, 620))
        self.init_ui()
        self.load_defaults()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        main = wx.BoxSizer(wx.VERTICAL)

        form = wx.FlexGridSizer(rows=8, cols=2, vgap=10, hgap=10)

        # Scope
        form.Add(wx.StaticText(panel, label="Scope:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.scope_choice = AccessibleChoice(panel, choices=["Global", "Account"])
        self.scope_choice.SetSelection(0)
        self.scope_choice.init_accessible("Signature scope")
        self.scope_choice.Bind(wx.EVT_CHOICE, self.on_scope_changed)
        form.Add(self.scope_choice, 1, wx.EXPAND)

        # Account
        form.Add(wx.StaticText(panel, label="Account:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.account_input = AccessibleTextCtrl(panel, value="")
        self.account_input.init_accessible("Account email")
        form.Add(self.account_input, 1, wx.EXPAND)

        # Enabled
        form.Add(wx.StaticText(panel, label="Enabled:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.enabled_chk = wx.CheckBox(panel, label="Use signature")
        self.enabled_chk.SetValue(True)
        form.Add(self.enabled_chk, 1, wx.EXPAND)

        # Apply to
        form.Add(wx.StaticText(panel, label="Apply To:"), 0, wx.ALIGN_CENTER_VERTICAL)
        apply_row = wx.BoxSizer(wx.HORIZONTAL)
        self.apply_new = wx.CheckBox(panel, label="New")
        self.apply_reply = wx.CheckBox(panel, label="Reply")
        self.apply_forward = wx.CheckBox(panel, label="Forward")
        self.apply_new.SetValue(True)
        self.apply_reply.SetValue(True)
        self.apply_forward.SetValue(True)
        apply_row.Add(self.apply_new, 0, wx.RIGHT, 10)
        apply_row.Add(self.apply_reply, 0, wx.RIGHT, 10)
        apply_row.Add(self.apply_forward, 0)
        form.Add(apply_row, 1, wx.EXPAND)

        # Position
        form.Add(wx.StaticText(panel, label="Position:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.position_choice = AccessibleChoice(panel, choices=["Bottom", "Top"])
        self.position_choice.SetSelection(0)
        self.position_choice.init_accessible("Signature position")
        form.Add(self.position_choice, 1, wx.EXPAND)

        # Separator
        form.Add(wx.StaticText(panel, label="Separator:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.separator_chk = wx.CheckBox(panel, label="Add standard signature separator (-- )")
        self.separator_chk.SetValue(True)
        form.Add(self.separator_chk, 1, wx.EXPAND)

        # HTML
        form.Add(wx.StaticText(panel, label="HTML Signature:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.use_html_chk = wx.CheckBox(panel, label="Use HTML signature when sending HTML")
        self.use_html_chk.SetValue(False)
        form.Add(self.use_html_chk, 1, wx.EXPAND)

        form.AddGrowableCol(1, 1)
        main.Add(form, 0, wx.EXPAND | wx.ALL, 10)

        # Signature Text
        main.Add(wx.StaticText(panel, label="Signature (Plain Text):"), 0, wx.LEFT | wx.RIGHT, 10)
        self.sig_text = AccessibleTextCtrl(panel, style=wx.TE_MULTILINE)
        self.sig_text.init_accessible("Signature plain text")
        main.Add(self.sig_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Signature HTML
        main.Add(wx.StaticText(panel, label="Signature (HTML):"), 0, wx.LEFT | wx.RIGHT, 10)
        self.sig_html = AccessibleTextCtrl(panel, style=wx.TE_MULTILINE)
        self.sig_html.init_accessible("Signature HTML")
        main.Add(self.sig_html, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons
        btns = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = AccessibleButton(panel, label="Save")
        save_btn.init_accessible("Save signature settings", announce=False)
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        delete_btn = AccessibleButton(panel, label="Clear This Scope")
        delete_btn.init_accessible("Clear scope settings", announce=False)
        delete_btn.Bind(wx.EVT_BUTTON, self.on_clear_scope)
        close_btn = AccessibleButton(panel, label="Close")
        close_btn.init_accessible("Close", announce=False)
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        btns.Add(save_btn, 0, wx.RIGHT, 10)
        btns.Add(delete_btn, 0, wx.RIGHT, 10)
        btns.Add(close_btn, 0)
        main.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(main)

    def on_scope_changed(self, event):
        is_account = self.scope_choice.GetStringSelection() == "Account"
        self.account_input.Enable(is_account)
        if not is_account:
            self.account_input.SetValue("")
        self.load_defaults()

    def _get_pref_store(self):
        prefs = config.get("signature_prefs", {})
        if not isinstance(prefs, dict):
            prefs = {}
        prefs.setdefault("global", {})
        prefs.setdefault("accounts", {})
        return prefs

    def _get_scope_key(self):
        scope = self.scope_choice.GetStringSelection().lower()
        if scope == "global":
            return ("global", None)
        account = self.account_input.GetValue().strip().lower()
        return ("account", account)

    def load_defaults(self):
        prefs = self._get_pref_store()
        scope, account = self._get_scope_key()

        data = {}
        if scope == "global":
            data = prefs.get("global", {})
        else:
            data = (prefs.get("accounts") or {}).get(account, {})

        self.enabled_chk.SetValue(bool(data.get("enabled", False)))
        apply_to = data.get("apply_to") or {}
        self.apply_new.SetValue(bool(apply_to.get("new", True)))
        self.apply_reply.SetValue(bool(apply_to.get("reply", True)))
        self.apply_forward.SetValue(bool(apply_to.get("forward", True)))
        self.position_choice.SetSelection(0 if data.get("position", "bottom") == "bottom" else 1)
        self.separator_chk.SetValue(bool(data.get("separator", True)))
        self.use_html_chk.SetValue(bool(data.get("use_html", False)))
        self.sig_text.SetValue(data.get("text", ""))
        self.sig_html.SetValue(data.get("html", ""))

    def on_save(self, event):
        prefs = self._get_pref_store()
        scope, account = self._get_scope_key()
        if scope == "account" and not account:
            speaker.speak("Account email is required")
            return

        data = {
            "enabled": self.enabled_chk.GetValue(),
            "text": self.sig_text.GetValue(),
            "html": self.sig_html.GetValue(),
            "use_html": self.use_html_chk.GetValue(),
            "position": "bottom" if self.position_choice.GetSelection() == 0 else "top",
            "separator": self.separator_chk.GetValue(),
            "apply_to": {
                "new": self.apply_new.GetValue(),
                "reply": self.apply_reply.GetValue(),
                "forward": self.apply_forward.GetValue()
            }
        }

        if scope == "global":
            prefs["global"] = data
        else:
            prefs["accounts"][account] = data

        config.set("signature_prefs", prefs)
        speaker.speak("Signature settings saved")

    def on_clear_scope(self, event):
        prefs = self._get_pref_store()
        scope, account = self._get_scope_key()

        if scope == "global":
            prefs["global"] = {}
        else:
            if account in prefs.get("accounts", {}):
                prefs["accounts"].pop(account, None)

        config.set("signature_prefs", prefs)
        self.load_defaults()
        speaker.speak("Signature settings cleared")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
            return
        event.Skip()
