
import wx
import logging
from ...core.account_manager import AccountManager
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleListCtrl, AccessibleButton
from ...core.event_bus import EventBus, Events
from .account_dialog import AccountDialog

logger = logging.getLogger(__name__)

class ManageAccountsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Manage Accounts", size=(600, 400))
        self.account_manager = AccountManager()
        self.accounts = []
        self.init_ui()
        self.load_accounts()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # List
        self.list = AccessibleListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.init_accessible("Accounts list", "Use arrow keys to navigate accounts.")
        self.list.InsertColumn(0, "Email", width=250)
        self.list.InsertColumn(1, "IMAP Server", width=150)
        self.list.InsertColumn(2, "SMTP Server", width=150)
        
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_double_click)

        vbox.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.add_btn = AccessibleButton(panel, label="Add Account")
        self.add_btn.init_accessible("Add account button", announce=False)
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        btn_sizer.Add(self.add_btn, 0, wx.RIGHT, 10)

        self.edit_btn = AccessibleButton(panel, label="Edit Account")
        self.edit_btn.init_accessible("Edit account button", announce=False)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.on_edit)
        btn_sizer.Add(self.edit_btn, 0, wx.RIGHT, 10)

        self.remove_btn = AccessibleButton(panel, label="Remove Account")
        self.remove_btn.init_accessible("Remove account button", announce=False)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_remove)
        btn_sizer.Add(self.remove_btn, 0, wx.RIGHT, 10)

        self.close_btn = AccessibleButton(panel, label="Close")
        self.close_btn.init_accessible("Close button", announce=False)
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        btn_sizer.Add(self.close_btn, 0)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        panel.SetSizer(vbox)

    def load_accounts(self):
        self.list.DeleteAllItems()
        self.accounts = self.account_manager.get_accounts()
        
        for account in self.accounts:
            idx = self.list.InsertItem(self.list.GetItemCount(), account['email'])
            self.list.SetItem(idx, 1, account['imap_host'])
            self.list.SetItem(idx, 2, account['smtp_host'])
            # Store account index or ID if needed, but we have self.accounts which matches index order
            # self.list.SetItemData(idx, account['id']) # if listctrl supports it

        if self.accounts:
            self.list.Select(0)
            self.list.Focus(0)
        else:
             speaker.speak("No accounts found.")

    def on_add(self, event):
        dlg = AccountDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.load_accounts()
            speaker.speak("Account list updated.")
        dlg.Destroy()

    def on_edit(self, event):
        idx = self.list.GetFirstSelected()
        if idx == -1:
            speaker.speak("No account selected.")
            return

        if idx < len(self.accounts):
            account_data = self.accounts[idx]
            dlg = AccountDialog(self, account_data=account_data)
            if dlg.ShowModal() == wx.ID_OK:
                self.load_accounts()
                speaker.speak("Account updated.")
            dlg.Destroy()

    def on_remove(self, event):
        idx = self.list.GetFirstSelected()
        if idx == -1:
            speaker.speak("No account selected.")
            return

        if idx < len(self.accounts):
            email = self.accounts[idx]['email']
            if wx.MessageBox(f"Are you sure you want to delete account {email}?\nThis will remove all downloaded emails for this account.", 
                             "Confirm Delete", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
                
                if self.account_manager.delete_account(email):
                    speaker.speak("Account deleted.")
                    self.load_accounts()
                    EventBus.publish(Events.ACCOUNT_ADDED, None) # Trigger refresh of folder list in main frame
                    # Consider adding an ACCOUNT_REMOVED or ACCOUNTS_CHANGED event.
                else:
                    wx.MessageBox("Failed to delete account.", "Error", wx.OK | wx.ICON_ERROR)
    
    def on_double_click(self, event):
        self.on_edit(event)

    def on_close(self, event):
        self.EndModal(wx.ID_CANCEL)

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()
