import threading
import time
from .accessibility import speaker


class AudibleProgress:
    """
    Simple audible progress indicator for long operations.
    Announces a message immediately and repeats every interval seconds.
    """
    def __init__(self, message: str, interval: int = 5):
        self.message = message
        self.interval = max(3, interval)
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        speaker.speak(self.message)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop_event.wait(self.interval):
            speaker.speak(self.message)

    def stop(self):
        self._stop_event.set()
