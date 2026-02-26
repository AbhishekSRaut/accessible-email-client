import os
import sys

def get_appdata_dir() -> str:
    """
    Returns the absolute path to the application's data directory in %APPDATA%.
    Ensures the directory exists before returning.
    """
    if sys.platform == 'win32':
        appdata = os.getenv('APPDATA')
        if not appdata:
            appdata = os.path.expanduser('~')
    else:
        # Fallback for non-Windows systems
        appdata = os.path.expanduser('~/.config')
        
    app_dir = os.path.join(appdata, "AccessibleEmailClient")
    
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
        
    return app_dir
