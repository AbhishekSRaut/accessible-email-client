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
- **📁 Smart Folder Rules**: Automatically organize emails based on custom rules
- **🔔 Customizable Notifications**: Per-folder and per-sender notification sounds
- **💾 Offline Support**: Local email caching for offline reading
- **🧵 Thread Management**: Expand and collapse email threads seamlessly
- **📎 Attachment Support**: Download and manage email attachments
- **🎨 HTML Email Rendering**: Accessible HTML rendering with semantic structure

## 🚀 Quick Start

### For End Users

**Download the latest release:**
1. Visit the [Releases](https://github.com/abhisheksraut/accessible_email_client/releases) page
2. Download the installer for your platform
3. Run the installer and follow the setup wizard
4. Launch the application and add your first email account

### For Developers

#### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

#### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abhisheksraut/accessible_email_client.git
   cd accessible_email_client
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

## 📖 User Guide

### Adding Your First Email Account

1. Launch the application
2. Press `Alt` to open the menu bar
3. Navigate to **Account** → **Add Account** (or press `Ctrl+A`)
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
- **note for zoho mail:** you need to enable imap access to make it functional. [click here to know more](https://www.zoho.com/mail/help/imap-access.html)
- **Other providers**: Check your email provider's security settings

### Managing Accounts

- **Switch Accounts**: Account menu → Select account
- **Edit Account**: Account menu → Manage Accounts → Select account → Edit
- **Remove Account**: Account menu → Manage Accounts → Select account → Remove

### Navigating Emails

- **Arrow Keys**: Navigate through email list
- **Right Arrow**: Expand email thread
- **Left Arrow**: Collapse email thread
- **Tab**: Move focus to email content area
- **Enter**: Open selected email
- **Ctrl Left Arrow/Right**: Navigate between pages (100 emails per page)

### Reading Emails

When viewing an email:
- **Tab**: Move between email content and action buttons
- **Arrow Keys**: Navigate within email content
- Screen readers will announce headings, links, and lists properly

### Email Actions

Available actions (accessible via keyboard):
- **Reply**: `Alt+Shift+R`
- **Reply All**: `Alt + Shift + A`
- **Forward**: `Alt + Shift + F`
- **Delete**: `Delete` key
- **Compose New**: `Ctrl+N`

### Creating Smart Folder Rules

1. Go to **Tools** → **Manage Rules**
2. Click **Add Rule**
3. Configure:
   - **Rule Name**: Give your rule a descriptive name
   - **Conditions**: Define sender or subject criteria
   - **Action**: Choose target folder
4. Save the rule

**Example**: Create a "Family" folder and automatically move emails from specific family members.

### Customizing Notifications

1. Go to **Tools** → **Notification Settings**
2. Configure:
   - **Global notification sound**: Default for all emails
   - **Per-folder sounds**: Different sound for specific folders
   - **Per-sender sounds**: Unique sound for important contacts

### Accessing Help

- **Help Menu**: Press `Alt+H` to access the help menu
- **README**: Help → View README (displays this documentation)
- **Keyboard Shortcuts**: Help → Keyboard Shortcuts

## 🛠️ Technical Details

### Architecture

The application follows a modular architecture:

- **UI Layer** (`ui/`): wxPython-based user interface
  - Main frame and menus
  - Panels (folder list, email list, message viewer)
  - Dialogs (compose, settings, account management)
  
- **Core Layer** (`core/`): Business logic
  - IMAP/SMTP clients
  - Account management with secure credential storage
  - Email caching and offline support
  - Rule engine for smart folders
  - Notification system
  
- **Database Layer** (`database/`): SQLite-based persistence
  - Email cache
  - Account metadata
  - User preferences
  
- **Accessibility Layer** (`utils/`): Accessibility helpers
  - Screen reader integration
  - Accessible widgets
  - Progress feedback

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

## importent note for mack / linux users:
**i tested only on windows, hence i am not aware of its usibility in mack / linux.**
**i am not sure regarding availibility and functionality of wxpython and other libraries used in this project in these operating systems.**

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

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/accessible_email_client/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/accessible_email_client/discussions)

## 🔒 Security

This application stores credentials securely using the system keyring. Passwords are never stored in plain text.

If you discover a security vulnerability, please email [YOUR_EMAIL] instead of using the issue tracker.

---

**Made with ❤️ for the visually impaired community**
