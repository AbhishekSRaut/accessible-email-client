"""
Launcher script for Accessible Email Client
This script uses absolute imports and can be used as PyInstaller entry point
"""

import sys
import os

# Add the parent directory to Python path so we can import accessible_email_client
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = sys._MEIPASS
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))
    # Add parent directory to path
    parent_dir = os.path.dirname(application_path)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import wx
import logging
from accessible_email_client.ui.main_frame import MainFrame
from accessible_email_client.core.configuration import config

def main():
    debug_env = os.environ.get("AEC_DEBUG", "").strip().lower() in ["1", "true", "yes", "y", "on"]
    debug_cfg = config.get_bool("debug", False)
    if debug_env or debug_cfg:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
