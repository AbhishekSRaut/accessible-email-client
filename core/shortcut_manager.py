
import wx
import logging
from typing import Dict, Tuple, Callable
from .configuration import config

logger = logging.getLogger(__name__)

class ShortcutManager:
    def __init__(self):
        # Action ID -> (description, default_accel_string, global_accel)
        self.registry: Dict[str, Tuple[str, str, bool]] = {}
        # Action ID -> callback
        self.callbacks: Dict[str, Callable] = {}
        # Action ID -> current_accel_string
        self.current_shortcuts: Dict[str, str] = {}

    def _is_alnum_keycode(self, keycode: int) -> bool:
        return (ord("0") <= keycode <= ord("9")) or (ord("A") <= keycode <= ord("Z"))

    def _is_valid_shortcut(self, shortcut_str: str) -> bool:
        if not shortcut_str:
            return False
        entry = wx.AcceleratorEntry()
        if not entry.FromString(shortcut_str):
            return False
        keycode = entry.GetKeyCode()
        flags = entry.GetFlags()

        if self._is_alnum_keycode(keycode):
            if not (flags & (wx.ACCEL_CTRL | wx.ACCEL_ALT)):
                return False
        return True

    def register(self, action_id: str, description: str, default_shortcut: str, callback: Callable = None, global_accel: bool = True):
        """
        Register an action with a default shortcut.
        global_accel: If True, added to main window accelerator table. If False, explicit check needed.
        """
        self.registry[action_id] = (description, default_shortcut, global_accel)
        
        # Load override if exists, else use default
        saved = config.get("shortcuts", {})
        saved_shortcut = saved.get(action_id, default_shortcut)
        if self._is_valid_shortcut(saved_shortcut):
            self.current_shortcuts[action_id] = saved_shortcut
        elif self._is_valid_shortcut(default_shortcut):
            self.current_shortcuts[action_id] = default_shortcut
        else:
            self.current_shortcuts[action_id] = ""
            logger.warning(f"Invalid shortcut for {action_id}; cleared.")
        
        if callback:
            self.callbacks[action_id] = callback

    def update_shortcut(self, action_id: str, new_shortcut: str):
        if action_id in self.registry:
            if not self._is_valid_shortcut(new_shortcut):
                logger.info(f"Rejected invalid shortcut for {action_id}: {new_shortcut}")
                return
            self.current_shortcuts[action_id] = new_shortcut
            self._save()

    def reset_to_defaults(self):
        for action_id, (desc, default, _) in self.registry.items():
            if self._is_valid_shortcut(default):
                self.current_shortcuts[action_id] = default
            else:
                self.current_shortcuts[action_id] = ""
        self._save()

    def _save(self):
        config.set("shortcuts", self.current_shortcuts)

    def get_shortcut(self, action_id: str) -> str:
        return self.current_shortcuts.get(action_id, "")

    def get_description(self, action_id: str) -> str:
        if action_id in self.registry:
            return self.registry[action_id][0]
        return action_id

    def get_all_shortcuts(self) -> Dict[str, str]:
        return self.current_shortcuts

    def build_accelerator_table(self, window: wx.Window):
        entries = []
        
        for action_id, shortcut_str in self.current_shortcuts.items():
            if not shortcut_str: continue
            
            # Check if global
            if action_id in self.registry and not self.registry[action_id][2]:
                continue
            
            # If no callback, we can't register global accel easily unless window handles it by ID?
            # We need a callback to bind.
            if action_id not in self.callbacks:
                continue
                
            accel_entry = wx.AcceleratorEntry()
            if accel_entry.FromString(shortcut_str):
                # We need a new ID for this command
                wx_id = wx.NewIdRef()
                entries.append(wx.AcceleratorEntry(accel_entry.GetFlags(), accel_entry.GetKeyCode(), wx_id))
                
                # Bind the event on the window to the callback
                window.Bind(wx.EVT_MENU, self.callbacks[action_id], id=wx_id)
        
        accel_table = wx.AcceleratorTable(entries)
        window.SetAcceleratorTable(accel_table)

    def matches_event(self, action_id: str, event: wx.KeyEvent) -> bool:
        """
        Checks if the given key event matches the shortcut for the action.
        """
        shortcut = self.current_shortcuts.get(action_id)
        if not shortcut:
            return False
            
        entry = wx.AcceleratorEntry()
        if not entry.FromString(shortcut):
            return False
            
        target_flags = entry.GetFlags()
        target_key = entry.GetKeyCode()
        
        return self._matches_keycode_and_mods(target_flags, target_key, event.GetKeyCode(),
                                              event.ControlDown(), event.AltDown(), event.ShiftDown())

    def matches_key(self, action_id: str, keycode: int, mods: int) -> bool:
        """
        Checks if the given keycode/modifiers match the shortcut for the action.
        mods should use wx.MOD_* flags.
        """
        shortcut = self.current_shortcuts.get(action_id)
        if not shortcut:
            return False

        entry = wx.AcceleratorEntry()
        if not entry.FromString(shortcut):
            return False

        target_flags = entry.GetFlags()
        target_key = entry.GetKeyCode()

        return self._matches_keycode_and_mods(
            target_flags,
            target_key,
            keycode,
            bool(mods & wx.MOD_CONTROL),
            bool(mods & wx.MOD_ALT),
            bool(mods & wx.MOD_SHIFT),
        )

    def _matches_keycode_and_mods(self, target_flags: int, target_key: int, evt_key: int,
                                  ctrl: bool, alt: bool, shift: bool) -> bool:
        if ord("a") <= evt_key <= ord("z"):
            evt_key = ord(chr(evt_key).upper())

        evt_flags = 0
        if ctrl: evt_flags |= wx.ACCEL_CTRL
        if alt: evt_flags |= wx.ACCEL_ALT
        if shift: evt_flags |= wx.ACCEL_SHIFT

        if (target_flags & (wx.ACCEL_CTRL | wx.ACCEL_ALT | wx.ACCEL_SHIFT)) != evt_flags:
            return False

        return target_key == evt_key

# Global instance
shortcut_manager = ShortcutManager()
