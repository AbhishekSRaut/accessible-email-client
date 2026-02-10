
import wx
import logging
from ...core.account_manager import AccountManager
from ...core.imap_client import IMAPClient
from ...core.smtp_client import SMTPClient
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleTextCtrl, AccessibleButton
from ...core.event_bus import EventBus, Events

logger = logging.getLogger(__name__)

class AddAccountDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Add New Email Account", size=(400, 500))
        self.account_manager = AccountManager()
        self.init_ui()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Form Layout
        grid = wx.FlexGridSizer(rows=8, cols=2, vgap=10, hgap=10)
        
        # Email
        grid.Add(wx.StaticText(panel, label="Email Address:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.email_ctrl = AccessibleTextCtrl(panel)
        self.email_ctrl.init_accessible("Email address")
        grid.Add(self.email_ctrl, 1, wx.EXPAND)

        # Password
        grid.Add(wx.StaticText(panel, label="App Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.password_ctrl = AccessibleTextCtrl(panel, style=wx.TE_PASSWORD)
        self.password_ctrl.init_accessible("App password")
        grid.Add(self.password_ctrl, 1, wx.EXPAND)

        # App-specific confirmation
        grid.Add(wx.StaticText(panel, label="App Password Only:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.app_password_confirm = wx.CheckBox(panel, label="I am using an app-specific password")
        self.app_password_confirm.SetValue(True)
        grid.Add(self.app_password_confirm, 1, wx.EXPAND)

        # IMAP Host
        grid.Add(wx.StaticText(panel, label="IMAP Server:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.imap_host_ctrl = AccessibleTextCtrl(panel, value="imap.gmail.com")
        self.imap_host_ctrl.init_accessible("IMAP server")
        grid.Add(self.imap_host_ctrl, 1, wx.EXPAND)

        # IMAP Port
        grid.Add(wx.StaticText(panel, label="IMAP Port:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.imap_port_ctrl = AccessibleTextCtrl(panel, value="993")
        self.imap_port_ctrl.init_accessible("IMAP port")
        grid.Add(self.imap_port_ctrl, 1, wx.EXPAND)

        # SMTP Host
        grid.Add(wx.StaticText(panel, label="SMTP Server:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.smtp_host_ctrl = AccessibleTextCtrl(panel, value="smtp.gmail.com")
        self.smtp_host_ctrl.init_accessible("SMTP server")
        grid.Add(self.smtp_host_ctrl, 1, wx.EXPAND)

        # SMTP Port
        grid.Add(wx.StaticText(panel, label="SMTP Port:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.smtp_port_ctrl = AccessibleTextCtrl(panel, value="465")
        self.smtp_port_ctrl.init_accessible("SMTP port")
        grid.Add(self.smtp_port_ctrl, 1, wx.EXPAND)
        
        # Growable columns
        grid.AddGrowableCol(1, 1)

        vbox.Add(grid, 1, wx.EXPAND | wx.ALL, 15)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.test_btn = AccessibleButton(panel, label="Test Connection")
        self.test_btn.init_accessible("Test connection button", announce=False)
        self.test_btn.Bind(wx.EVT_BUTTON, self.on_test)
        btn_sizer.Add(self.test_btn, 0, wx.RIGHT, 10)

        self.save_btn = AccessibleButton(panel, label="Save Account")
        self.save_btn.init_accessible("Save account button", announce=False)
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        btn_sizer.Add(self.save_btn, 0, wx.RIGHT, 10)

        self.cancel_btn = AccessibleButton(panel, label="Cancel")
        self.cancel_btn.init_accessible("Cancel button", announce=False)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.Add(self.cancel_btn, 0)

        vbox.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)
        
        panel.SetSizer(vbox)

    def on_test(self, event):
        email = self.email_ctrl.GetValue()
        password = self.password_ctrl.GetValue()
        imap_host = self.imap_host_ctrl.GetValue()
        imap_port = int(self.imap_port_ctrl.GetValue())

        if not self.app_password_confirm.GetValue():
            wx.MessageBox("Please confirm you are using an app-specific password.", "Error", wx.OK | wx.ICON_ERROR)
            return

        speaker.speak("Testing connection, please wait...")
        
        # Test IMAP logic
        try:
            from imapclient import IMAPClient as LibIMAP
            server = LibIMAP(imap_host, port=imap_port, ssl=True)
            server.login(email, password)
            server.logout()
            wx.MessageBox("Connection Successful!", "Success", wx.OK | wx.ICON_INFORMATION)
            speaker.speak("Connection successful")
        except Exception as e:
            wx.MessageBox(f"Connection Failed: {e}", "Error", wx.OK | wx.ICON_ERROR)
            speaker.speak("Connection failed")

    def on_save(self, event):
        email = self.email_ctrl.GetValue()
        password = self.password_ctrl.GetValue()
        imap_host = self.imap_host_ctrl.GetValue()
        imap_port = int(self.imap_port_ctrl.GetValue())
        smtp_host = self.smtp_host_ctrl.GetValue()
        smtp_port = int(self.smtp_port_ctrl.GetValue())

        if not email or not password:
            wx.MessageBox("Please enter email and password.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not self.app_password_confirm.GetValue():
            wx.MessageBox("App-specific password confirmation is required.", "Error", wx.OK | wx.ICON_ERROR)
            return

        success = self.account_manager.add_account(email, password, imap_host, imap_port, smtp_host, smtp_port)
        if success:
            speaker.speak(f"Account {email} saved successfully.")
            EventBus.publish(Events.ACCOUNT_ADDED, email)
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox("Failed to save account. It might already exist.", "Error", wx.OK | wx.ICON_ERROR)
            speaker.speak("Failed to save account")

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()
