# Accessible Email Client

A **fully accessible, free, desktop email client** built with wxPython, designed primarily for **visually impaired users**. This client prioritizes accessibility above all else, providing a keyboard-first, screen reader-friendly email experience.

> **Why this project exists:**  
> This project started because existing email clients were frustrating and inaccessible in daily use.  
> The goal is not to replace every feature of big providers, but to make email calm, predictable, and accessible by default.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## ✨ Key Features

- **🎯 Accessibility-First Design**: Fully compatible with NVDA and other screen readers
- **⌨️ Keyboard-First Navigation**: Complete functionality without mouse interaction
- **📧 Multi-Account Support**: Manage multiple email accounts simultaneously
- **🔐 Secure Authentication**: Uses app-specific passwords with encrypted local storage
- **📁 Smart Folder Rules**: Automatically organize emails based on custom rules (per-account scoping)
- **🔔 Customizable Notifications**: Per-folder and per-sender notification sounds with background polling
- **💾 Offline Support**: Local email caching for offline reading
- **🧵 Thread Management**: Expand and collapse email threads seamlessly
- **📎 Attachment Support**: Download and manage email attachments
- **🎨 HTML Email Rendering**: Accessible HTML rendering with semantic structure
- **🔒 Single Instance**: Only one instance runs at a time; re-launching restores the existing window
- **📌 System Tray**: Minimizes to tray on close for background notifications

## 🚀 Quick Start

### For End Users

**Download the latest release:**
1. Visit the [Releases](https://github.com/AbhishekSRaut/accessible-email-client/releases) page
2. Download the installer for your platform
3. Run the installer and follow the setup wizard
4. Launch the application and add your first email account

### For Developers

#### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Git

#### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AbhishekSRaut/accessible-email-client.git
   cd accessible-email-client
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python -m accessible_email_client.main
   ```

#### Building with PyInstaller

```bash
python -m PyInstaller accessible_email_client/launcher.py --name AccessibleEmailClient --onedir --windowed
```

The `launcher.py` entry point handles PyInstaller-specific setup (WebView2Loader.dll preloading, hidden imports, STA COM initialization).

#### Development Mode

To enable debug logging, set the `AEC_DEBUG` environment variable:

```bash
# Windows (PowerShell)
$env:AEC_DEBUG="1"
python -m accessible_email_client.main

# Windows (CMD)
set AEC_DEBUG=1
python -m accessible_email_client.main

# macOS/Linux
AEC_DEBUG=1 python -m accessible_email_client.main
```

Or set `"debug": true` in the application settings.

## 📖 User Guide

### Adding Your First Email Account

1. Launch the application
2. Press `Alt` to open the menu bar
3. Navigate to **Account** → **Add Account** (or press `Ctrl+Shift+A`)
4. Fill in the following details:
   - **Email Address**: Your full email address
   - **App Password**: Your app-specific password (see below)
   - **IMAP Server**: Your email provider's IMAP server (e.g., `imap.gmail.com`)
   - **IMAP Port**: Usually `993` for SSL/TLS
   - **SMTP Server**: Your email provider's SMTP server (e.g., `smtp.gmail.com`)
   - **SMTP Port**: Usually `465` or `587`
5. Check the confirmation box to verify you're using an app-specific password
6. Click **Save** or press `Enter`

#### Getting App-Specific Passwords

**Important**: This client requires app-specific passwords, NOT your regular account password.

- **Gmail**: [Create app password](https://support.google.com/accounts/answer/185833)
- **Outlook/Hotmail**: [Create app password](https://support.microsoft.com/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944)
- **Zoho Mail**: Settings → Security → App Passwords
- **Note for Zoho Mail:** You need to enable IMAP access to make it functional. [Click here to know more](https://www.zoho.com/mail/help/imap-access.html)
- **Other providers**: Check your email provider's security settings

### Managing Accounts

- **Switch Accounts**: Click on the account name in the folder tree
- **Edit Account**: Account menu → Manage Accounts → Select account → Edit
- **Remove Account**: Account menu → Manage Accounts → Select account → Remove

### Navigating Emails

- **Arrow Keys**: Navigate through email list
- **Right Arrow**: Expand email thread
- **Left Arrow**: Collapse email thread
- **Tab**: Move focus to email content area
- **Enter**: Open selected email
- **Escape**: Return focus from message viewer to email list
- **Ctrl+Right / Ctrl+Left**: Navigate between pages (100 emails per page)
- **Alt+Shift+L**: Focus the email list from anywhere

### Reading Emails

When viewing an email:
- **Tab**: Move between email content and action buttons (Reply, Reply All, Forward, etc.)
- **Shift+Tab**: Return to message list
- **Escape**: Return focus from WebView to email list
- **Arrow Keys**: Navigate within email content
- Screen readers will announce headings, links, and lists properly

### Email Actions

Available actions (accessible via keyboard):
- **Compose New**: `Ctrl+N`
- **Reply**: `Alt+Shift+R`
- **Reply All**: `Alt+Shift+A`
- **Forward**: `Alt+Shift+F`
- **Delete**: `Delete` key
- **Archive**: `Ctrl+Alt+A`
- **Refresh**: `F5`
- **Exit Application**: `Ctrl+Q`

### Creating Smart Folder Rules

Rules are **per-account** — a rule created for one email account only applies to that account's emails.

1. Go to **Folder** → **Manage Rules**
2. Click **Add Rule**
3. Configure:
   - **Rule Name**: Give your rule a descriptive name
   - **Conditions**: Define criteria by sender, subject, or recipient
   - **Action**: Choose target folder and whether to move or copy
   - **Inbox Behavior**: Choose "Move only" (removes from Inbox) or uncheck to copy (keep in Inbox)
4. Save the rule

**Example**: Create a "Family" folder and automatically move emails from specific family members.

### System Tray & Background Notifications

- When you close the window (`Alt+F4`), the app **minimizes to the system tray** instead of exiting
- Email polling continues in the background (checks every 60 seconds)
- **Toast notifications** appear for new emails
- **Right-click the tray icon** to open the app or exit completely
- Use `Ctrl+Q` or tray **Exit** to fully quit the application

### Single Instance

Only one instance of the application runs at a time. If you try to launch it again while it's running (including in the background tray), the existing window will be restored and brought to focus.

### Customizing Notifications

1. Go to **Settings** → **Settings...**
2. Configure:
   - **Silent mode**: Toggle with `Ctrl+S`
   - **Notification Sounds**: Configure sound rules by scope (global/account), type (default/folder/sender), and sound file

### Settings

Access via **Settings** menu:
- **Normalize HTML for screen readers**: Converts complex HTML into a simpler structure for easier navigation
- **Keyboard Shortcuts**: View and customize all keyboard shortcuts (`Ctrl+K`)
- **Signatures**: Create global or per-account email signatures (plain text and HTML, with position control)

### Accessing Help

- **Help Menu**: Press `Alt+H` to access the help menu
- **User Guide**: Help → Open User Guide (displays the HTML documentation)
- **Contact Developer**: Help → Contact Developer (opens a compose dialog)
- **GitHub**: Help → Open Developer GitHub

## 🛠️ Technical Details

### Architecture

The application follows a modular architecture:

- **UI Layer** (`ui/`): wxPython-based user interface
  - Main frame with system tray integration
  - Panels (folder list, email list, message viewer with WebView2)
  - Dialogs (compose, settings, account management, rules, shortcuts)
  
- **Core Layer** (`core/`): Business logic
  - IMAP/SMTP clients with thread-safe locking
  - Account management with secure credential storage (system keyring)
  - Email caching and offline support
  - Rule engine for smart folders (per-account scoping)
  - Notification system with customizable sounds
  - Email polling for background notifications
  - Shortcut manager with customizable key bindings
  
- **Database Layer** (`database/`): SQLite-based persistence
  - Email cache (headers, bodies, flags)
  - Account metadata
  - Folder rules with account scoping
  - Automatic schema migrations
  
- **Utilities** (`utils/`): Accessibility and system helpers
  - Screen reader integration (accessible_output2)
  - Accessible widgets (ListCtrl, TextCtrl, Buttons, etc.)
  - Audible progress feedback
  - Single-instance guard (Windows mutex + TCP socket IPC)
  - AppData directory management

### Supported Email Providers

This client works with any email provider that supports IMAP/SMTP with app-specific passwords:

- ✅ Gmail
- ✅ Outlook/Hotmail
- ✅ Zoho Mail
- ✅ Yahoo Mail
- ✅ ProtonMail Bridge
- ✅ Custom domain email (with IMAP/SMTP)

### Dependencies

- **wxPython**: Cross-platform GUI framework
- **accessible_output2**: Screen reader integration
- **keyring**: Secure credential storage
- **IMAPClient**: IMAP protocol implementation
- **yagmail**: SMTP email sending
- **windows-toasts**: Native Windows notifications
- **pystray**: System tray integration
- **Pillow**: Image processing
- **BeautifulSoup4**: HTML parsing and normalization

## ⚠️ Platform Support Note (macOS / Linux)

This project has been **developed and tested only on Windows**.

At the moment:
- I cannot confirm full usability on **macOS or Linux**
- Availability and behavior of **wxPython and other dependencies** may vary across platforms
- Some features (especially accessibility-related behavior and single-instance guard) may not work as intended outside Windows

Contributions, testing reports, and platform-specific improvements from macOS and Linux users are **very welcome**.

## ⚠️ Project Status

> **Important Notice:**  
> This project is built primarily for personal use.  
> It is shared as-is, without guarantees of long-term maintenance or feature requests.  
> Contributions are welcome, but support is not guaranteed.

This means:
- ✅ The code is open source and free to use
- ✅ Bug reports and pull requests are appreciated
- ⚠️ Feature requests may not be implemented
- ⚠️ Updates may be sporadic based on personal needs
- ⚠️ No commitment to ongoing support or maintenance

If you find this useful, feel free to fork it and adapt it to your needs!

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test with a screen reader (NVDA recommended)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- **Accessibility is paramount**: All features must be fully keyboard-accessible
- **Test with screen readers**: Verify changes work with NVDA or similar tools
- **Follow existing patterns**: Maintain consistency with the codebase
- **Document your changes**: Update relevant documentation

## 📋 Known Limitations

- OAuth2 authentication is not supported (app-specific passwords only)
- HTML normalization is best-effort for complex layouts
- Offline cache does not include attachments
- Advanced search and saved searches not yet implemented
- Single-instance guard is Windows-only (uses Windows named mutex)

## 🗺️ Roadmap

- [ ] OAuth2 support for providers that require it
- [ ] Unified inbox view
- [ ] Advanced search functionality
- [ ] Contact management and auto-complete
- [ ] Email templates
- [ ] Scheduled sending
- [ ] Improved HTML rendering
- [ ] macOS and Linux installers

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

This means:
- ✅ You can use, modify, and distribute this software freely
- ✅ You can use it for commercial purposes
- ⚠️ If you modify and distribute it, you must release your changes under AGPL-3.0
- ⚠️ If you run a modified version as a network service, you must make the source available

See the [LICENSE](LICENSE) file for full details.

## 🙏 Acknowledgments

- Built with [wxPython](https://wxpython.org/)
- Screen reader support via [accessible_output2](https://github.com/accessibleapps/accessible_output2)
- Inspired by the need for truly accessible email clients

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/AbhishekSRaut/accessible-email-client/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AbhishekSRaut/accessible-email-client/discussions)

## 🔒 Security

This application stores credentials securely using the system keyring. Passwords are never stored in plain text.

If you discover a security vulnerability, please email [raut.abhishek@zohomail.in] instead of using the issue tracker.

---

**Made with ❤️ for the visually impaired community**
