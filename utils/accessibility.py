
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

    def speak(self, text: str, interrupt: bool = False):
        """
        Speak the given text using the active screen reader.
        """
        if not text:
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
