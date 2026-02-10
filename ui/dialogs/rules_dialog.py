
import wx
import logging
from ...core.rule_manager import RuleManager
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleTextCtrl, AccessibleButton, AccessibleListBox, AccessibleChoice

logger = logging.getLogger(__name__)

class RulesDialog(wx.Dialog):
    def __init__(self, parent, folders=None):
        super().__init__(parent, title="Manage Rules", size=(600, 500))
        self.rule_manager = RuleManager()
        self.folders = folders or []
        self.init_ui()
        self.load_rules()
        self.Center()
        
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Rules List
        list_label = wx.StaticText(panel, label="Existing Rules:")
        main_sizer.Add(list_label, 0, wx.ALL, 5)
        
        self.rules_list = AccessibleListBox(panel, choices=[])
        self.rules_list.init_accessible("Rules list", "Select a rule to delete")
        main_sizer.Add(self.rules_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Delete Button
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.edit_btn = AccessibleButton(panel, label="Edit Selected Rule")
        self.edit_btn.init_accessible("Edit rule button", announce=False)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.on_edit_rule)
        btn_row.Add(self.edit_btn, 0, wx.RIGHT, 10)

        self.delete_btn = AccessibleButton(panel, label="Delete Selected Rule")
        self.delete_btn.init_accessible("Delete rule button", announce=False)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.on_delete_rule)
        btn_row.Add(self.delete_btn, 0)
        main_sizer.Add(btn_row, 0, wx.ALL, 5)
        
        # Add New Rule Section
        box = wx.StaticBox(panel, label="Add New Rule")
        box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        grid = wx.FlexGridSizer(rows=5, cols=2, vgap=10, hgap=10)
        
        # Name
        grid.Add(wx.StaticText(panel, label="Rule Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name_input = AccessibleTextCtrl(panel)
        self.name_input.init_accessible("Rule name")
        grid.Add(self.name_input, 1, wx.EXPAND)
        
        # Condition Field
        grid.Add(wx.StaticText(panel, label="If:"), 0, wx.ALIGN_CENTER_VERTICAL)
        cond_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.cond_field = AccessibleChoice(panel, choices=["Sender", "Subject"])
        self.cond_field.SetSelection(0)
        self.cond_field.init_accessible("Condition field")
        
        self.cond_value = AccessibleTextCtrl(panel)
        self.cond_value.init_accessible("Condition value")
        
        cond_sizer.Add(self.cond_field, 0, wx.RIGHT, 5)
        cond_sizer.Add(wx.StaticText(panel, label="contains"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        cond_sizer.Add(self.cond_value, 1, wx.EXPAND)
        
        grid.Add(cond_sizer, 1, wx.EXPAND)
        
        # Action
        grid.Add(wx.StaticText(panel, label="Move to:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.action_folder = AccessibleChoice(panel, choices=self.folders)
        if self.folders:
            self.action_folder.SetSelection(0)
        self.action_folder.init_accessible("Target folder")
        grid.Add(self.action_folder, 1, wx.EXPAND)

        # Exclusive move
        grid.Add(wx.StaticText(panel, label="Inbox Behavior:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.exclusive_move = wx.CheckBox(panel, label="Move only (do not keep in Inbox)")
        self.exclusive_move.SetValue(True)
        grid.Add(self.exclusive_move, 1, wx.EXPAND)

        hint = wx.StaticText(panel, label="Tip: Move only removes it from Inbox. If unchecked, it will be copied to the target folder and remain in Inbox.")
        hint.Wrap(520)
        box_sizer.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        grid.AddGrowableCol(1, 1)
        box_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        
        self.add_btn = AccessibleButton(panel, label="Add Rule")
        self.add_btn.init_accessible("Add rule button", announce=False)
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add_rule)
        box_sizer.Add(self.add_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        main_sizer.Add(box_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Close Button
        self.close_btn = AccessibleButton(panel, label="Close")
        self.close_btn.init_accessible("Close button", announce=False)
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        main_sizer.Add(self.close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        panel.SetSizer(main_sizer)

    def load_rules(self):
        self.rules_list.Clear()
        self.params_map = {} # index -> rule_id
        self.rules_map = {} # index -> rule object
        
        rules = self.rule_manager.get_rules()
        for idx, rule in enumerate(rules):
            name = rule['name']
            cond = rule['conditions']
            act = rule['actions']
            
            # Simplified display string
            cond_str = ", ".join([f"{k} contains '{v}'" for k, v in cond.items()])
            mode = "Move only" if act.get("exclusive", True) else "Copy (keep in Inbox)"
            act_str = f"{mode} -> '{act.get('move_to', 'Unknown')}'"
            
            display = f"{name}: If {cond_str}, {act_str}"
            self.rules_list.Append(display)
            self.params_map[idx] = rule['id']
            self.rules_map[idx] = rule
            
        if self.rules_list.GetCount() > 0:
            self.rules_list.SetSelection(0)
        else:
            self.rules_list.Append("No rules defined")
            self.rules_list.SetSelection(0)
            self.delete_btn.Disable()
            self.edit_btn.Disable()
        if self.rules_list.GetCount() > 0:
            self.delete_btn.Enable()
            self.edit_btn.Enable()
        self._reset_edit_state()

    def _reset_edit_state(self):
        self.editing_rule_id = None
        self.add_btn.SetLabel("Add Rule")
        self.exclusive_move.SetValue(True)

    def on_add_rule(self, event):
        name = self.name_input.GetValue().strip()
        cond_field = self.cond_field.GetStringSelection().lower()
        cond_val = self.cond_value.GetValue().strip()
        target_folder = self.action_folder.GetStringSelection()
        
        if not name or not cond_val or not target_folder:
            speaker.speak("Please fill all fields")
            wx.MessageBox("Please fill all fields", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        conditions = {cond_field: cond_val}
        actions = {"move_to": target_folder, "exclusive": self.exclusive_move.GetValue()}
        
        if self.editing_rule_id:
            success = self.rule_manager.update_rule(self.editing_rule_id, name, conditions, actions)
            if success:
                speaker.speak("Rule updated")
                self.name_input.Clear()
                self.cond_value.Clear()
                self.load_rules()
            else:
                speaker.speak("Failed to update rule")
                wx.MessageBox("Failed to update rule", "Error", wx.OK | wx.ICON_ERROR)
        else:
            if self.rule_manager.add_rule(name, conditions, actions):
                speaker.speak("Rule added")
                self.name_input.Clear()
                self.cond_value.Clear()
                self.load_rules()
                self.delete_btn.Enable()
            else:
                speaker.speak("Failed to add rule")
                wx.MessageBox("Failed to add rule", "Error", wx.OK | wx.ICON_ERROR)

    def on_delete_rule(self, event):
        idx = self.rules_list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
            
        rule_str = self.rules_list.GetString(idx)
        if rule_str == "No rules defined":
            return
            
        rule_id = self.params_map.get(idx)
        if rule_id:
            if self.rule_manager.delete_rule(rule_id):
                speaker.speak("Rule deleted")
                self.load_rules()
            else:
                speaker.speak("Failed to delete rule")

    def on_edit_rule(self, event):
        idx = self.rules_list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        rule_str = self.rules_list.GetString(idx)
        if rule_str == "No rules defined":
            return

        rule = self.rules_map.get(idx)
        if not rule:
            return

        self.editing_rule_id = rule["id"]
        self.add_btn.SetLabel("Update Rule")
        self.name_input.SetValue(rule.get("name", ""))

        conditions = rule.get("conditions", {})
        if "sender" in conditions:
            self.cond_field.SetSelection(0)
            self.cond_value.SetValue(conditions.get("sender", ""))
        elif "subject" in conditions:
            self.cond_field.SetSelection(1)
            self.cond_value.SetValue(conditions.get("subject", ""))

        actions = rule.get("actions", {})
        target = actions.get("move_to")
        if target and target in self.folders:
            self.action_folder.SetStringSelection(target)
        self.exclusive_move.SetValue(bool(actions.get("exclusive", True)))

    def on_close(self, event):
        self.Destroy()
        
    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()
