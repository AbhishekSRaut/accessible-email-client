
import logging
import threading
import winsound
from windows_toasts import Toast, WindowsToaster
from typing import Optional, Callable, Dict, Any
from .configuration import config

logger = logging.getLogger(__name__)

class NotificationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.toaster = WindowsToaster('Accessible Email Client')
        self.silent_mode = False
        self.prefs = self._load_prefs()

    def _default_prefs(self) -> Dict[str, Any]:
        return {
            "default": "SystemAsterisk",
            "folders": {},
            "senders": {},
            "accounts": {}
        }

    def _normalize_prefs(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        base = self._default_prefs()
        if not isinstance(prefs, dict):
            return base
        base["default"] = prefs.get("default") or base["default"]
        base["folders"] = prefs.get("folders") or {}
        base["senders"] = prefs.get("senders") or {}
        base["accounts"] = prefs.get("accounts") or {}
        return base

    def _load_prefs(self) -> Dict[str, Any]:
        prefs = config.get("notification_prefs", {})
        return self._normalize_prefs(prefs)

    def _save_prefs(self):
        config.set("notification_prefs", self.prefs)

    def get_preferences(self) -> Dict[str, Any]:
        return self.prefs

    def set_preferences(self, prefs: Dict[str, Any]):
        self.prefs = self._normalize_prefs(prefs)
        self._save_prefs()

    def set_silent_mode(self, enabled: bool):
        self.silent_mode = enabled
        logger.info(f"Silent mode set to {enabled}")

    def show_toast(self, title: str, message: str, on_click: Optional[Callable] = None):
        """
        Show a Windows Toast notification.
        """
        try:
            toast = Toast()
            toast.text_fields = [title, message]
            
            if on_click:
                toast.on_activated = lambda _: on_click()
            
            self.toaster.show_toast(toast)
            logger.info(f"Shown toast: {title}")
        except Exception as e:
            logger.error(f"Failed to show toast: {e}")

    def play_sound(self, category: str = 'default', sender: Optional[str] = None, account_email: Optional[str] = None):
        """
        Play a sound based on category or sender.
        Prioritizes sender specific sound, then folder/category, then account/default.
        """
        if self.silent_mode:
            return

        sound_to_play = self._resolve_sound(category, sender, account_email)

        if sound_to_play:
            try:
                # Run in a separate thread so it doesn't block UI
                threading.Thread(target=self._play_sound_thread, args=(sound_to_play,)).start()
            except Exception as e:
                logger.error(f"Failed to play sound: {e}")

    def _resolve_sound(self, category: str, sender: Optional[str], account_email: Optional[str]) -> Optional[str]:
        prefs = self.prefs or self._default_prefs()
        sound = prefs.get("default") or "SystemAsterisk"

        sender_key = sender.lower() if sender else None
        category_key = category.lower() if category else None

        # Global overrides
        if sender_key:
            sound = prefs.get("senders", {}).get(sender_key, sound)
        if category_key:
            sound = prefs.get("folders", {}).get(category_key, sound)

        # Account overrides
        if account_email:
            acc_key = account_email.lower()
            acc = prefs.get("accounts", {}).get(acc_key, {})
            sound = acc.get("default", sound)
            if sender_key:
                sound = acc.get("senders", {}).get(sender_key, sound)
            if category_key:
                sound = acc.get("folders", {}).get(category_key, sound)

        return sound

    def _play_sound_thread(self, sound):
        try:
            # winsound.PlaySound supports system event aliases (like 'SystemAsterisk') or filenames
            flags = winsound.SND_ASYNC
            if '.' in sound: # Assume file path
                 flags = winsound.SND_FILENAME | winsound.SND_ASYNC
            else:
                 flags = winsound.SND_ALIAS | winsound.SND_ASYNC
                 
            winsound.PlaySound(sound, flags)
        except Exception as e:
            logger.error(f"Error playing sound '{sound}': {e}")

notification_manager = NotificationManager()
