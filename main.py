
import wx
import logging
import os
from .ui.main_frame import MainFrame
from .core.configuration import config

def main():
    debug_env = os.environ.get("AEC_DEBUG", "").strip().lower() in ["1", "true", "yes", "y", "on"]
    debug_cfg = config.get_bool("debug", False)
    if debug_env or debug_cfg:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.disable(logging.CRITICAL)
    
    # Initialize wx App
    app = wx.App(False)
    
    # Create Main Frame
    frame = MainFrame()
    
    # Start Main Loop
    app.MainLoop()

if __name__ == "__main__":
    main()
