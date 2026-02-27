
import wx
import logging
import os
import sys
from .ui.main_frame import MainFrame
from .core.configuration import config

def main():
    # --- Single-instance check ---
    from .utils.single_instance import instance_guard
    if instance_guard.is_another_instance_running():
        # Another instance exists — signal it to show and exit
        instance_guard.signal_existing_instance()
        print("Another instance is already running. Restoring it.")
        sys.exit(0)

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

    # Cleanup single-instance resources
    instance_guard.cleanup()

if __name__ == "__main__":
    main()
