# Build Instructions

## Building Releases with PyInstaller

### Prerequisites

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

### Building the Executable

#### Option 1: Using the Spec File (Recommended)

```bash
# From the project root directory
pyinstaller build.spec
```

This will create:
- `dist/AccessibleEmailClient.exe` - Standalone executable
- `build/` - Temporary build files (can be deleted)

#### Option 2: Command Line (Quick Build)

```bash
pyinstaller --clean --noconfirm --onefile --windowed ^
  --name "AccessibleEmailClient" ^
  --add-data "accessible_email_client/database/schema.sql;accessible_email_client/database" ^
  --hidden-import accessible_output2 ^
  --hidden-import keyring ^
  --hidden-import keyring.backends ^
  --hidden-import keyring.backends.Windows ^
  --hidden-import IMAPClient ^
  --hidden-import yagmail ^
  --hidden-import windows_toasts ^
  --hidden-import pystray ^
  --hidden-import PIL ^
  --hidden-import wx ^
  --hidden-import wx.html2 ^
  accessible_email_client/main.py
```

**Note**: The `^` is for line continuation in Windows CMD. In PowerShell, use backtick `` ` `` instead.

### Build Flags Explained

- `--onefile` - Bundle everything into a single .exe
- `--windowed` (or `-w`) - No console window (GUI app)
- `--clean` - Clean PyInstaller cache before building
- `--noconfirm` - Replace output directory without asking
- `--add-data` - Include non-Python files (like schema.sql)
- `--hidden-import` - Explicitly include modules that PyInstaller might miss
- `--name` - Name of the output executable

### Testing the Build

```bash
# Run the executable
dist\AccessibleEmailClient.exe
```

Test thoroughly:
- ✅ Application launches without errors
- ✅ Can add email accounts
- ✅ Can send/receive emails
- ✅ Screen reader compatibility
- ✅ All dialogs and features work

### Creating an Installer (Optional)

If you have Inno Setup installed:

1. Update `installer/AccessibleEmailClient.iss`:
   - Set `MyAppExeDir` to your `dist` folder path
   - Update version number if needed

2. Compile with Inno Setup:
   ```bash
   iscc installer\AccessibleEmailClient.iss
   ```

3. This creates `AccessibleEmailClient-Setup.exe` in the `installer` directory

## Troubleshooting

### Missing DLLs
If you get DLL errors, ensure all dependencies are installed in your Python environment.

### Import Errors
Add missing modules to `--hidden-import` or the `hiddenimports` list in `build.spec`.

### Large File Size
The executable will be 50-100 MB due to wxPython and dependencies. This is normal.

### Antivirus False Positives
PyInstaller executables sometimes trigger antivirus warnings. This is a known issue. You may need to:
- Sign the executable with a code signing certificate
- Submit to antivirus vendors as a false positive

## Build Checklist

Before creating a release:

- [ ] Update version number in `installer/AccessibleEmailClient.iss`
- [ ] Test the executable on a clean Windows machine
- [ ] Verify all features work in the compiled version
- [ ] Test with NVDA screen reader
- [ ] Create release notes
- [ ] Tag the release in git
