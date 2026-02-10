
import wx
import logging
from ...core.account_manager import AccountManager
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleTextCtrl, AccessibleButton
from ...core.event_bus import EventBus, Events

logger = logging.getLogger(__name__)

class AccountDialog(wx.Dialog):
    def __init__(self, parent, account_data=None):
        title = "Edit Account" if account_data else "Add New Email Account"
        super().__init__(parent, title=title, size=(400, 500))
        self.account_manager = AccountManager()
        self.account_data = account_data
        self.init_ui()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Form Layout
        grid = wx.FlexGridSizer(rows=8, cols=2, vgap=10, hgap=10)
        
        # Defaults
        email_val = ""
        pass_val = ""
        imap_host_val = "imap.gmail.com"
        imap_port_val = "993"
        smtp_host_val = "smtp.gmail.com"
        smtp_port_val = "465"
        
        if self.account_data:
            email_val = self.account_data.get("email", "")
            imap_host_val = self.account_data.get("imap_host", "")
            imap_port_val = str(self.account_data.get("imap_port", 993))
            smtp_host_val = self.account_data.get("smtp_host", "")
            smtp_port_val = str(self.account_data.get("smtp_port", 465))
            # Try to fetch password
            stored_pass = self.account_manager.get_password(email_val)
            if stored_pass:
                pass_val = stored_pass

        # Email
        grid.Add(wx.StaticText(panel, label="Email Address:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.email_ctrl = AccessibleTextCtrl(panel, value=email_val)
        self.email_ctrl.init_accessible("Email address")
        grid.Add(self.email_ctrl, 1, wx.EXPAND)

        # Password
        grid.Add(wx.StaticText(panel, label="App Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.password_ctrl = AccessibleTextCtrl(panel, value=pass_val, style=wx.TE_PASSWORD)
        self.password_ctrl.init_accessible("App password")
        grid.Add(self.password_ctrl, 1, wx.EXPAND)

        # App-specific confirmation
        grid.Add(wx.StaticText(panel, label="App Password Only:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.app_password_confirm = wx.CheckBox(panel, label="I am using an app-specific password")
        self.app_password_confirm.SetValue(True)
        grid.Add(self.app_password_confirm, 1, wx.EXPAND)

        # IMAP Host
        grid.Add(wx.StaticText(panel, label="IMAP Server:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.imap_host_ctrl = AccessibleTextCtrl(panel, value=imap_host_val)
        self.imap_host_ctrl.init_accessible("IMAP server")
        grid.Add(self.imap_host_ctrl, 1, wx.EXPAND)

        # IMAP Port
        grid.Add(wx.StaticText(panel, label="IMAP Port:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.imap_port_ctrl = AccessibleTextCtrl(panel, value=imap_port_val)
        self.imap_port_ctrl.init_accessible("IMAP port")
        grid.Add(self.imap_port_ctrl, 1, wx.EXPAND)

        # SMTP Host
        grid.Add(wx.StaticText(panel, label="SMTP Server:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.smtp_host_ctrl = AccessibleTextCtrl(panel, value=smtp_host_val)
        self.smtp_host_ctrl.init_accessible("SMTP server")
        grid.Add(self.smtp_host_ctrl, 1, wx.EXPAND)

        # SMTP Port
        grid.Add(wx.StaticText(panel, label="SMTP Port:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.smtp_port_ctrl = AccessibleTextCtrl(panel, value=smtp_port_val)
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

        if not self.app_password_confirm.GetValue():
            wx.MessageBox("Please confirm you are using an app-specific password.", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        try:
             imap_port = int(self.imap_port_ctrl.GetValue())
        except ValueError:
             wx.MessageBox("Invalid IMAP Port", "Error", wx.OK | wx.ICON_ERROR)
             return

        speaker.speak("Testing connection, please wait...")
        
        try:
            from ...core.imap_client import IMAPClient # Or import specifically if needed
            # Use basic imaplib or the IMAPClient wrapper if convenient.
            # Using standard imaplib for raw test to avoid wrapper overhead/logic
            import imaplib
            import ssl
            
            ctx = ssl.create_default_context()
            server = imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=ctx)
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
        smtp_host = self.smtp_host_ctrl.GetValue()
        
        try:
            imap_port = int(self.imap_port_ctrl.GetValue())
            smtp_port = int(self.smtp_port_ctrl.GetValue())
        except ValueError:
             wx.MessageBox("Invalid Port Number", "Error", wx.OK | wx.ICON_ERROR)
             return

        if not email:
            wx.MessageBox("Please enter email address.", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        # Password check: required on add; on edit, required if email changed.
        if not password:
             wx.MessageBox("Please enter password.", "Error", wx.OK | wx.ICON_ERROR)
             return

        if not self.app_password_confirm.GetValue():
            wx.MessageBox("App-specific password confirmation is required.", "Error", wx.OK | wx.ICON_ERROR)
            return

        success = False
        if self.account_data:
            # Update mode
            old_email = self.account_data.get("email")
            success = self.account_manager.update_account(
                old_email, email, password, imap_host, imap_port, smtp_host, smtp_port
            )
        else:
            # Add mode
            success = self.account_manager.add_account(
                email, password, imap_host, imap_port, smtp_host, smtp_port
            )

        if success:
            action = "updated" if self.account_data else "added"
            speaker.speak(f"Account {email} {action} successfully.")
            EventBus.publish(Events.ACCOUNT_ADDED, email) # Or ACCOUNT_UPDATED? Setup uses ADDED to refresh list.
            # ACCOUNT_ADDED usually triggers refresh; update events can be added if needed.
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox("Failed to save account.", "Error", wx.OK | wx.ICON_ERROR)
            speaker.speak("Failed to save account")

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()
