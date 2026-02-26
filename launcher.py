"""
Launcher script for Accessible Email Client
This script uses absolute imports and can be used as PyInstaller entry point
"""

import sys
import os

# WebView2 requires Single-Threaded Apartment (STA) COM initialization
sys.coinit_flags = 2

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
import ctypes
from accessible_email_client.ui.main_frame import MainFrame
from accessible_email_client.core.configuration import config

# Preload WebView2Loader.dll to help wxWidgets C++ find it in PyInstaller's _internal folder
if getattr(sys, 'frozen', False):
    try:
        dll_path1 = os.path.join(sys._MEIPASS, "wx", "WebView2Loader.dll")
        dll_path2 = os.path.join(sys._MEIPASS, "WebView2Loader.dll")
        if os.path.exists(dll_path1):
            ctypes.CDLL(dll_path1)
        elif os.path.exists(dll_path2):
            ctypes.CDLL(dll_path2)
    except Exception as e:
        print(f"Warning: Failed to preload WebView2Loader.dll: {e}")


# Explicitly import dynamically loaded modules so PyInstaller bundles them automatically
# This removes the need for --hidden-import arguments in the build command
import accessible_output2
import keyring
import keyring.backends
# Windows backend specifically needed
import keyring.backends.Windows
import imapclient
import yagmail
import windows_toasts
import pystray
import PIL
import wx.html2
import bs4

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
