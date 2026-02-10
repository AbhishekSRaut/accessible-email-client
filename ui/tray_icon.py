
import threading
import logging
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

logger = logging.getLogger(__name__)

class TrayIconManager:
    def __init__(self, on_open, on_exit):
        self.on_open = on_open
        self.on_exit = on_exit
        self.icon = None
        self._thread = None

    def _create_image(self):
        # Create a simple icon image
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        dc = ImageDraw.Draw(image)
        dc.rectangle(
            (width // 4, height // 4, width * 3 // 4, height * 3 // 4),
            fill=(0, 0, 255)
        )
        return image

    def _setup_icon(self):
        steps = [
            item('Open', self._on_open_clicked, default=True),
            item('Exit', self._on_exit_clicked)
        ]
        self.icon = pystray.Icon("AccessibleEmailClient", self._create_image(), "Accessible Email Client", menu=pystray.Menu(*steps))

    def _on_open_clicked(self, icon, item):
        if self.on_open:
            self.on_open()

    def _on_exit_clicked(self, icon, item):
        self.icon.stop()
        if self.on_exit:
            self.on_exit()

    def start(self):
        self._setup_icon()
        self._thread = threading.Thread(target=self.icon.run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()
