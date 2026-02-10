import wx
from .accessibility import speaker


class AccessibleMixin:
    """
    Mixin to provide consistent screen reader announcements on focus.
    Call init_accessible after widget construction.
    """
    def init_accessible(self, label: str, hint: str = "", announce: bool = True):
        self._accessible_label = label or ""
        self._accessible_hint = hint or ""
        self._accessible_announce = announce
        self.Bind(wx.EVT_SET_FOCUS, self._on_accessible_focus)

    def set_accessible_label(self, label: str):
        self._accessible_label = label or ""

    def set_accessible_hint(self, hint: str):
        self._accessible_hint = hint or ""

    def _on_accessible_focus(self, event):
        if not getattr(self, "_accessible_announce", True):
            event.Skip()
            return
        text = self._accessible_label
        if self._accessible_hint:
            text = f"{text}. {self._accessible_hint}" if text else self._accessible_hint
        if text:
            speaker.speak(text)
        event.Skip()


class AccessibleTextCtrl(AccessibleMixin, wx.TextCtrl):
    pass


class AccessibleButton(AccessibleMixin, wx.Button):
    pass


class AccessibleListCtrl(AccessibleMixin, wx.ListCtrl):
    pass


class AccessibleTreeCtrl(AccessibleMixin, wx.TreeCtrl):
    pass


class AccessibleListBox(AccessibleMixin, wx.ListBox):
    pass


class AccessibleChoice(AccessibleMixin, wx.Choice):
    pass
