
import wx
import logging
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleTreeCtrl
from ...core.event_bus import EventBus
from ...core.event_bus import Events
from ...core.account_manager import AccountManager
from ...core.imap_client import IMAPClient

logger = logging.getLogger(__name__)

class FolderListPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.imap_clients = {} # email -> IMAPClient
        self._initial_selected = False
        self.init_ui()
        
        # Subscribe to events
        EventBus.subscribe(Events.ACCOUNT_ADDED, self.on_account_added)
        
        # Load existing accounts
        self.load_accounts()

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(self, label="Folders")
        sizer.Add(label, 0, wx.ALL, 5)

        self.tree = AccessibleTreeCtrl(self, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self.tree.init_accessible("Folder list", "Use arrow keys to browse folders")
        self.root = self.tree.AddRoot("Root")
        
        
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_selection_changed)
        self.tree.Bind(wx.EVT_SET_FOCUS, self.on_focus)

        sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

    def load_accounts(self):
        self.tree.DeleteChildren(self.root)
        self.imap_clients = {}
        accounts = self.account_manager.get_accounts()
        for account in accounts:
            self.add_account_node(account['email'])

    def on_account_added(self, email):
        wx.CallAfter(self.add_account_node, email)

    def add_account_node(self, email):
        try:
            # Create a client for this account
            client = IMAPClient(email)
            self.imap_clients[email] = client
            
            # Add account node
            account_node = self.tree.AppendItem(self.root, email)
            self.tree.SetItemData(account_node, {"type": "account", "email": email})
            
            # Fetch and add folders
            folders = client.list_folders()
            for folder in folders:
                folder_name = folder['name']
                # Clean up folder name if needed (e.g. remove delimiters)
                folder_node = self.tree.AppendItem(account_node, folder_name)
                self.tree.SetItemData(folder_node, {"type": "folder", "email": email, "name": folder_name})

            # Default to Inbox once on first load
            if not self._initial_selected:
                inbox_node = None
                child, cookie = self.tree.GetFirstChild(account_node)
                while child.IsOk():
                    name = self.tree.GetItemText(child)
                    if name.lower() == "inbox":
                        inbox_node = child
                        break
                    child, cookie = self.tree.GetNextChild(account_node, cookie)
                if inbox_node:
                    self.tree.SelectItem(inbox_node)
                    self._initial_selected = True
            
            self.tree.Expand(account_node)
            logger.info(f"Loaded folders for {email}")
            
        except Exception as e:
            logger.error(f"Failed to load folders for {email}: {e}")
            speaker.speak(f"Failed to load folders for {email}")

    def on_selection_changed(self, event):
        if not self.tree or not self.tree.GetHandle():
            return
            
        item = event.GetItem()
        if item and item.IsOk():
            try:
                data = self.tree.GetItemData(item)
                text = self.tree.GetItemText(item)
                
                if data and data.get("type") == "folder":
                    speaker.speak(f"Selected folder {text}")
                    # Publish event with account and folder info
                    EventBus.publish(Events.FOLDER_UPDATED, data)
                elif data and data.get("type") == "account":
                    speaker.speak(f"Account {text}")
                    
            except RuntimeError:
                pass 

    def on_focus(self, event):
        speaker.speak("Folder list")
        event.Skip()

    def get_selected_account(self):
        item = self.tree.GetSelection()
        if item and item.IsOk():
            data = self.tree.GetItemData(item)
            if data:
                return data.get('email')
        return None

    def refresh_folders(self, email):
        root = self.tree.GetRootItem()
        cookie = 0
        child, cookie = self.tree.GetFirstChild(root)
        
        account_node = None
        while child.IsOk():
            data = self.tree.GetItemData(child)
            if data and data.get('email') == email and data.get('type') == 'account':
                account_node = child
                break
            child, cookie = self.tree.GetNextChild(root, cookie)
            
        if account_node:
            self.tree.DeleteChildren(account_node)
            
            try:
                client = self.imap_clients.get(email)
                if not client:
                     client = IMAPClient(email)
                     self.imap_clients[email] = client
                     
                folders = client.list_folders()
                for folder in folders:
                    folder_name = folder['name']
                    folder_node = self.tree.AppendItem(account_node, folder_name)
                    self.tree.SetItemData(folder_node, {"type": "folder", "email": email, "name": folder_name})
                
                self.tree.Expand(account_node)
                
            except Exception as e:
                logger.error(f"Failed to refresh folders for {email}: {e}")
                speaker.speak("Failed to refresh folder list.")
