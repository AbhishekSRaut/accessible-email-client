
import wx
import wx.lib.mixins.listctrl as listmix
from ...core.shortcut_manager import shortcut_manager
from ...utils.accessible_widgets import AccessibleButton

class ShortcutsListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class ShortcutCaptureDialog(wx.Dialog):
    def __init__(self, parent, action_name):
        super().__init__(parent, title=f"Set Shortcut for '{action_name}'", size=(300, 150))
        self.key_str = ""
        self.init_ui()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(self, label="Press the new key combination...")
        sizer.Add(lbl, 0, wx.ALL | wx.CENTER, 10)
        
        self.display = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_CENTER)
        sizer.Add(self.display, 0, wx.ALL | wx.EXPAND, 10)
        
        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.ALL | wx.CENTER, 10)
        
        self.SetSizer(sizer)

    def on_key(self, event):
        mods = event.GetModifiers()
        key = event.GetKeyCode()

        if key == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        
        # Ignored keys
        if key in [wx.WXK_SHIFT, wx.WXK_CONTROL, wx.WXK_ALT, wx.WXK_COMMAND]:
            event.Skip()
            return

        has_ctrl_alt = bool(mods & (wx.MOD_CONTROL | wx.MOD_ALT))

        parts = []
        if mods & wx.MOD_CONTROL: parts.append("Ctrl")
        if mods & wx.MOD_ALT: parts.append("Alt")
        if mods & wx.MOD_SHIFT: parts.append("Shift")
        
        # Get key name
        if key < 128:
            key_char = chr(key)
            if key_char.isalnum() and not has_ctrl_alt:
                self.key_str = ""
                self.display.SetValue("Requires Ctrl or Alt")
                return
            key_name = key_char.upper()
        else:
            # Handle special keys roughly
            key_name = self._get_special_key_name(key)

        parts.append(key_name)
        self.key_str = "+".join(parts)
        self.display.SetValue(self.key_str)
    
    def _get_special_key_name(self, key):
        # Basic mapping for common special keys
        map = {
            wx.WXK_F1: "F1", wx.WXK_F2: "F2", wx.WXK_F3: "F3", wx.WXK_F4: "F4",
            wx.WXK_F5: "F5", wx.WXK_F6: "F6", wx.WXK_F7: "F7", wx.WXK_F8: "F8",
            wx.WXK_F9: "F9", wx.WXK_F10: "F10", wx.WXK_F11: "F11", wx.WXK_F12: "F12",
            wx.WXK_DELETE: "Delete", wx.WXK_BACK: "Back", wx.WXK_INSERT: "Insert",
            wx.WXK_HOME: "Home", wx.WXK_END: "End", wx.WXK_PAGEUP: "PgUp", wx.WXK_PAGEDOWN: "PgDn",
            wx.WXK_UP: "Up", wx.WXK_DOWN: "Down", wx.WXK_LEFT: "Left", wx.WXK_RIGHT: "Right",
            wx.WXK_RETURN: "Return", wx.WXK_ESCAPE: "Esc", wx.WXK_SPACE: "Space",
            wx.WXK_TAB: "Tab"
        }
        return map.get(key, "Unknown")

class ShortcutsDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Keyboard Shortcuts", size=(500, 400))
        self.init_ui()
        self.load_shortcuts()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.list = ShortcutsListCtrl(panel, wx.ID_ANY, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.list.InsertColumn(0, "Action", width=250)
        self.list.InsertColumn(1, "Shortcut", width=150)
        
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        btns_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.edit_btn = AccessibleButton(panel, label="Edit Shortcut")
        self.edit_btn.Bind(wx.EVT_BUTTON, self.on_edit)
        
        self.reset_btn = AccessibleButton(panel, label="Reset Defaults")
        self.reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        
        close_btn = AccessibleButton(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())

        btns_sizer.Add(self.edit_btn, 0, wx.ALL, 5)
        btns_sizer.Add(self.reset_btn, 0, wx.ALL, 5)
        btns_sizer.Add(close_btn, 0, wx.ALL, 5)

        sizer.Add(btns_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        panel.SetSizer(sizer)

    def load_shortcuts(self):
        self.list.DeleteAllItems()
        self.action_ids = []
        shortcuts = shortcut_manager.get_all_shortcuts()
        
        # Registry has descriptions
        for action_id, (desc, default, _) in shortcut_manager.registry.items():
            current = shortcuts.get(action_id, default)
            idx = self.list.InsertItem(self.list.GetItemCount(), desc)
            self.list.SetItem(idx, 1, current)
            self.action_ids.append(action_id)

    def on_edit(self, event):
        idx = self.list.GetFirstSelected()
        if idx == -1:
            return
            
        action_id = self.action_ids[idx]
        desc = shortcut_manager.get_description(action_id)
        
        dlg = ShortcutCaptureDialog(self, desc)
        if dlg.ShowModal() == wx.ID_OK:
            new_key = dlg.key_str
            if new_key:
                shortcut_manager.update_shortcut(action_id, new_key)
                self.list.SetItem(idx, 1, new_key)
        dlg.Destroy()

    def on_reset(self, event):
        shortcut_manager.reset_to_defaults()
        self.load_shortcuts()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()
