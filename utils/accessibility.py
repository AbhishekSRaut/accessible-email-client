
import logging
from accessible_output2.outputs import auto

logger = logging.getLogger(__name__)

class Speaker:
    """
    Wrapper for accessible_output2 to handle screen reader speech.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Speaker, cls).__new__(cls)
            try:
                cls._instance.output = auto.Auto()
            except Exception as e:
                logger.error(f"Failed to initialize accessible_output2: {e}")
                cls._instance.output = None
        return cls._instance

    def _is_window_visible(self):
        """Check if the main application window is visible."""
        try:
            import wx
            app = wx.GetApp()
            if app:
                top = app.GetTopWindow()
                if top and not top.IsShown():
                    return False
        except Exception:
            pass
        return True

    def speak(self, text: str, interrupt: bool = False):
        """
        Speak the given text using the active screen reader.
        Skip speech when the main window is hidden (running in background).
        """
        if not text:
            return

        # Don't speak when app is minimized to tray
        if not self._is_window_visible():
            return

        logger.info(f"Speaking: {text}")
        if self.output:
            try:
                self.output.speak(text, interrupt=interrupt)
            except Exception as e:
                logger.error(f"Error speaking text: {e}")

    def silence(self):
        """
        Stop speech immediately.
        """
        if self.output:
            try:
                self.output.silence()
            except Exception as e:
                logger.error(f"Error silencing speech: {e}")

# Global instance
speaker = Speaker()
