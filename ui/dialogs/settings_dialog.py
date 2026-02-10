import wx
from ...utils.accessible_widgets import AccessibleButton
from ...utils.accessibility import speaker
from ...core.notification_manager import notification_manager
from ...core.configuration import config


class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Settings", size=(500, 360))
        self.init_ui()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        main = wx.BoxSizer(wx.VERTICAL)

        # Accessibility toggles
        acc_box = wx.StaticBox(panel, label="Accessibility")
        acc_sizer = wx.StaticBoxSizer(acc_box, wx.VERTICAL)

        self.normalize_html_chk = wx.CheckBox(panel, label="Normalize HTML for screen readers")
        self.normalize_html_chk.SetValue(config.get_bool("normalize_html", True))
        acc_sizer.Add(self.normalize_html_chk, 0, wx.ALL, 8)

        main.Add(acc_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Notifications
        notif_box = wx.StaticBox(panel, label="Notifications")
        notif_sizer = wx.StaticBoxSizer(notif_box, wx.VERTICAL)

        self.silent_chk = wx.CheckBox(panel, label="Silent mode (no sound)")
        self.silent_chk.SetValue(notification_manager.silent_mode)
        notif_sizer.Add(self.silent_chk, 0, wx.ALL, 8)

        notif_btn = AccessibleButton(panel, label="Notification Sounds...")
        notif_btn.init_accessible("Notification sounds settings", announce=False)
        notif_btn.Bind(wx.EVT_BUTTON, self.on_open_notifications)
        notif_sizer.Add(notif_btn, 0, wx.ALL, 8)

        main.Add(notif_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Shortcuts
        shortcuts_box = wx.StaticBox(panel, label="Keyboard")
        shortcuts_sizer = wx.StaticBoxSizer(shortcuts_box, wx.VERTICAL)
        shortcuts_btn = AccessibleButton(panel, label="Keyboard Shortcuts...")
        shortcuts_btn.init_accessible("Keyboard shortcuts settings", announce=False)
        shortcuts_btn.Bind(wx.EVT_BUTTON, self.on_open_shortcuts)
        shortcuts_sizer.Add(shortcuts_btn, 0, wx.ALL, 8)

        main.Add(shortcuts_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Signatures
        sig_box = wx.StaticBox(panel, label="Signatures")
        sig_sizer = wx.StaticBoxSizer(sig_box, wx.VERTICAL)
        sig_btn = AccessibleButton(panel, label="Signatures...")
        sig_btn.init_accessible("Signature settings", announce=False)
        sig_btn.Bind(wx.EVT_BUTTON, self.on_open_signatures)
        sig_sizer.Add(sig_btn, 0, wx.ALL, 8)
        main.Add(sig_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons
        btns = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = AccessibleButton(panel, label="Save")
        save_btn.init_accessible("Save settings button", announce=False)
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        close_btn = AccessibleButton(panel, label="Close")
        close_btn.init_accessible("Close settings button", announce=False)
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        btns.Add(save_btn, 0, wx.RIGHT, 10)
        btns.Add(close_btn, 0)

        main.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(main)

    def on_save(self, event):
        config.set("normalize_html", self.normalize_html_chk.GetValue())
        notification_manager.set_silent_mode(self.silent_chk.GetValue())
        status = "enabled" if self.normalize_html_chk.GetValue() else "disabled"
        speaker.speak(f"Settings saved. HTML normalization {status}.")
        self.Close()

    def on_open_notifications(self, event):
        from .notification_settings import NotificationSettingsDialog
        dlg = NotificationSettingsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_open_shortcuts(self, event):
        from .shortcuts_dialog import ShortcutsDialog
        dlg = ShortcutsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_open_signatures(self, event):
        from .signature_settings import SignatureSettingsDialog
        dlg = SignatureSettingsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()
