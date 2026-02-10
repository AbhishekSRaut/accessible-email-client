
import wx
import wx.html2
import logging
import html
import os
from email.utils import getaddresses
from ...core.configuration import config
from ...utils.accessible_widgets import AccessibleListBox, AccessibleButton
from ...utils.accessibility import speaker
from ...utils.progress import AudibleProgress
from ...core.event_bus import EventBus
from ...core.event_bus import Events
from ...core.email_repository import EmailRepository
from ...core.shortcut_manager import shortcut_manager

logger = logging.getLogger(__name__)

class MessageViewerPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.webview = None
        self.imap_client = None
        self.current_email = None
        self.current_headers = {}
        self.current_attachments = []
        self._focus_list_accel_id = None
        self._webview_accel_ids = []
        self.init_ui()
        EventBus.subscribe(Events.EMAIL_SELECTED, self.on_email_selected)
        EventBus.subscribe(Events.EMAIL_OPENED, self.on_email_opened)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(self, label="Message Content")
        sizer.Add(label, 0, wx.ALL, 5)

        # Use WebView for accessible HTML rendering
        try:
            self.webview = wx.html2.WebView.New(self)
        except Exception as e:
            logger.error(f"Failed to initialize WebView: {e}")
            self.webview = None
            error_label = wx.StaticText(self, label="Error loading HTML viewer.")
            sizer.Add(error_label, 1, wx.EXPAND | wx.ALL, 5)
            return
        self.webview.Bind(wx.EVT_CHAR_HOOK, self.on_webview_key_down)
        self.webview.Bind(wx.EVT_KEY_DOWN, self.on_webview_key_down)
        try:
            self.webview.AddScriptMessageHandler("aec")
            self.webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.on_webview_script_message)
            self.webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.on_webview_loaded)
        except Exception as e:
            logger.warning(f"WebView script handler setup failed: {e}")
        self._install_webview_accel()

        # Placeholder content
        self.webview.SetPage("<h1>Select an email</h1><p>Select an email from the list to view its content.</p>", "")

        sizer.Add(self.webview, 1, wx.EXPAND | wx.ALL, 5)

        # Attachments panel
        attach_label = wx.StaticText(self, label="Attachments")
        sizer.Add(attach_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

        attach_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.attach_list = AccessibleListBox(self, choices=[])
        self.attach_list.init_accessible("Attachments list", "Select an attachment to download")
        self.download_btn = AccessibleButton(self, label="Download Attachment")
        self.download_btn.init_accessible("Download attachment button", announce=False)
        self.download_btn.Bind(wx.EVT_BUTTON, self.on_download_attachment)
        self.attach_list.Bind(wx.EVT_LISTBOX, self.on_attachment_selected)

        attach_sizer.Add(self.attach_list, 1, wx.ALL | wx.EXPAND, 4)
        attach_sizer.Add(self.download_btn, 0, wx.ALL, 4)
        sizer.Add(attach_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 5)

        # Actions panel below content
        actions_label = wx.StaticText(self, label="Actions")
        sizer.Add(actions_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)

        actions_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.back_to_list_btn = AccessibleButton(self, label="Back to Message List")
        self.back_to_list_btn.init_accessible("Back to message list button", announce=False)
        self.back_to_list_btn.Bind(wx.EVT_BUTTON, self.on_focus_message_list_accel)

        self.reply_btn = AccessibleButton(self, label="Reply")
        self.reply_btn.init_accessible("Reply button", announce=False)
        self.reply_all_btn = AccessibleButton(self, label="Reply All")
        self.reply_all_btn.init_accessible("Reply all button", announce=False)
        self.forward_btn = AccessibleButton(self, label="Forward")
        self.forward_btn.init_accessible("Forward button", announce=False)
        self.delete_btn = AccessibleButton(self, label="Delete")
        self.delete_btn.init_accessible("Delete button", announce=False)
        self.archive_btn = AccessibleButton(self, label="Archive")
        self.archive_btn.init_accessible("Archive button", announce=False)
        self.mark_read_btn = AccessibleButton(self, label="Mark Read/Unread")
        self.mark_read_btn.init_accessible("Mark read or unread button", announce=False)

        self.reply_btn.Bind(wx.EVT_BUTTON, self.on_reply)
        self.reply_all_btn.Bind(wx.EVT_BUTTON, self.on_reply_all)
        self.forward_btn.Bind(wx.EVT_BUTTON, self.on_forward)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        self.archive_btn.Bind(wx.EVT_BUTTON, self.on_archive)
        self.mark_read_btn.Bind(wx.EVT_BUTTON, self.on_toggle_read)

        actions_sizer.Add(self.back_to_list_btn, 0, wx.ALL, 4)
        actions_sizer.Add(self.reply_btn, 0, wx.ALL, 4)
        actions_sizer.Add(self.reply_all_btn, 0, wx.ALL, 4)
        actions_sizer.Add(self.forward_btn, 0, wx.ALL, 4)
        actions_sizer.Add(self.delete_btn, 0, wx.ALL, 4)
        actions_sizer.Add(self.archive_btn, 0, wx.ALL, 4)
        actions_sizer.Add(self.mark_read_btn, 0, wx.ALL, 4)

        sizer.Add(actions_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(sizer)

    def on_email_opened(self, email_data):
        """
        Callback for EMAIL_OPENED event. Fetch body and focus.
        """
        if self.webview:
            self.current_email = email_data
            # Fetch full body if needed
            account = email_data.get('account')
            folder = email_data.get('folder')
            uid = email_data.get('uid')
            
            if account and folder and uid:
                speaker.speak("Loading content...")
                progress = AudibleProgress("Loading content, please wait", interval=6)
                progress.start()
                try:
                    # Use repository
                    repo = EmailRepository(account)
                    body_data = repo.fetch_email_body(folder, uid)
                    
                    html = body_data.get('html', '')
                    text = body_data.get('text', '')
                    self.current_headers = body_data.get('headers', {})
                    self.current_attachments = body_data.get('attachments', []) or []
                    self._refresh_attachments()
                    
                    if html:
                        self.webview.SetPage(self._wrap_html(html), "")
                    elif text:
                        self.webview.SetPage(self._wrap_plain(text), "")
                    else:
                        self.webview.SetPage("<p>No body content found.</p>", "")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch body: {e}")
                    self.webview.SetPage(f"<p>Error loading content: {e}</p>", "")
                finally:
                    progress.stop()
            
            self.webview.SetFocus()
            speaker.speak("Content loaded and focused. Press Tab for commands or Shift+Tab for message list.")

    def on_email_selected(self, email_data):
        """
        Callback for EMAIL_SELECTED event. Show a lightweight preview.
        """
        if not self.webview:
            return

        subject = email_data.get('subject', 'No Subject')
        sender = email_data.get('sender', 'Unknown')
        
        html = f"""
        <h2>{subject}</h2>
        <p><b>From:</b> {sender}</p>
        <p><i>Press Enter or Tab to load full content.</i></p>
        """
        self.webview.SetPage(html, "")
        speaker.speak("Message selected")
        self.current_attachments = []
        self._refresh_attachments()

    def _refresh_attachments(self):
        self.attach_list.Clear()
        if not self.current_attachments:
            self.attach_list.Append("No attachments")
            self.attach_list.SetSelection(0)
            self.download_btn.Disable()
            self.download_btn.SetLabel("Download Attachment")
            return
        for att in self.current_attachments:
            name = att.get("filename", "attachment")
            ctype = att.get("content_type", "")
            self.attach_list.Append(f"{name} ({ctype})")
        self.attach_list.SetSelection(0)
        self.download_btn.Enable()
        self._update_download_label()

    def on_attachment_selected(self, event):
        self._update_download_label()
        event.Skip()

    def on_char_hook(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            top = self._get_top_frame()
            if top and hasattr(top, "email_list_panel"):
                top.email_list_panel.list.SetFocus()
                speaker.speak("Email list")
                return
        if shortcut_manager.matches_event("focus_message_list", event):
            top = self._get_top_frame()
            if top and hasattr(top, "email_list_panel"):
                top.email_list_panel.list.SetFocus()
                speaker.speak("Email list")
                return
        if shortcut_manager.matches_event("focus_actions", event):
            self.reply_btn.SetFocus()
            speaker.speak("Actions")
            return
        if keycode == wx.WXK_TAB:
            if self.handle_webview_tab(event):
                return
        event.Skip()

    def on_webview_key_down(self, event):
        keycode = event.GetKeyCode()
        mods = 0
        if hasattr(event, "GetModifiers"):
            mods = event.GetModifiers()
        else:
            if event.ControlDown(): mods |= wx.MOD_CONTROL
            if event.AltDown(): mods |= wx.MOD_ALT
            if event.ShiftDown(): mods |= wx.MOD_SHIFT

        if keycode == wx.WXK_ESCAPE:
            top = self._get_top_frame()
            if top and hasattr(top, "email_list_panel"):
                top.email_list_panel.list.SetFocus()
                speaker.speak("Email list")
                return
        if shortcut_manager.matches_key("focus_message_list", keycode, mods):
            top = self._get_top_frame()
            if top and hasattr(top, "email_list_panel"):
                top.email_list_panel.list.SetFocus()
                speaker.speak("Email list")
                return

        event.Skip()

    def on_webview_loaded(self, event):
        """Inject keyboard handler script after page loads."""
        # Note: Disabled script injection due to persistent 'Error running JavaScript: failed to evaluate'
        # errors on startup in compiled builds. WebView native accelerators should handle most shortcuts.
        # If specific key handling issues arise, consider re-enabling with checking for a fully loaded DOM.
        event.Skip()
    
    def _inject_script_safe(self, script):
        """Safely inject script with error handling."""
        try:
            if self.webview:
                self.webview.RunScript(script)
        except Exception as e:
            # This is non-critical, just log at debug level
            logger.debug(f"Script injection failed: {e}")

    def on_webview_script_message(self, event):
        try:
            msg = event.GetString().strip().upper()
        except Exception:
            msg = ""
        if msg == "R":
            self.on_reply_accel(None)
        elif msg == "A":
            self.on_reply_all_accel(None)
        elif msg == "F":
            self.on_forward_accel(None)
        elif msg == "L":
            self.on_focus_message_list_accel(None)

    def _install_webview_accel(self):
        if not self.webview:
            return
        for accel_id in self._webview_accel_ids:
            try:
                self.webview.Unbind(wx.EVT_MENU, id=accel_id)
            except Exception:
                pass
        self._webview_accel_ids = []

        entries = []
        action_bindings = {
            "focus_message_list": self.on_focus_message_list_accel,
            "reply": self.on_reply_accel,
            "reply_all": self.on_reply_all_accel,
            "forward": self.on_forward_accel,
            "delete": self.on_delete_accel,
            "archive": self.on_archive_accel,
            "focus_actions": self.on_focus_actions_accel,
        }
        for action_id, handler in action_bindings.items():
            shortcut = shortcut_manager.get_shortcut(action_id)
            if not shortcut:
                continue
            entry = wx.AcceleratorEntry()
            if entry.FromString(shortcut):
                wx_id = wx.NewIdRef()
                entries.append(wx.AcceleratorEntry(entry.GetFlags(), entry.GetKeyCode(), wx_id))
                self.webview.Bind(wx.EVT_MENU, handler, id=wx_id)
                self._webview_accel_ids.append(wx_id)

        # Fixed Alt+Shift fallbacks for message body focus
        fixed_alt_shift = [
            (ord("R"), self.on_reply_accel),
            (ord("A"), self.on_reply_all_accel),
            (ord("F"), self.on_forward_accel),
            (ord("L"), self.on_focus_message_list_accel),
        ]
        for keycode, handler in fixed_alt_shift:
            wx_id = wx.NewIdRef()
            entries.append(wx.AcceleratorEntry(wx.ACCEL_ALT | wx.ACCEL_SHIFT, keycode, wx_id))
            self.webview.Bind(wx.EVT_MENU, handler, id=wx_id)
            self._webview_accel_ids.append(wx_id)

        if entries:
            self.webview.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def on_focus_message_list_accel(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "email_list_panel"):
            top.email_list_panel.list.SetFocus()
            speaker.speak("Email list")

    def refresh_shortcuts(self):
        self._install_webview_accel()

    def on_reply_accel(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "on_reply"):
            top.on_reply(None)
            speaker.speak("Reply")

    def on_reply_all_accel(self, event):
        self.on_reply_all(None)

    def on_forward_accel(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "on_forward"):
            top.on_forward(None)
            speaker.speak("Forward")

    def on_delete_accel(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "email_list_panel"):
            top.email_list_panel.delete_selected()

    def on_archive_accel(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "email_list_panel"):
            top.email_list_panel.archive_selected()

    def on_focus_actions_accel(self, event):
        self.reply_btn.SetFocus()
        speaker.speak("Actions")

    def handle_webview_tab(self, event):
        focused = wx.Window.FindFocus()
        if focused and self.webview and focused is self.webview:
            if event.ShiftDown():
                top = self._get_top_frame()
                if top and hasattr(top, "email_list_panel"):
                    top.email_list_panel.list.SetFocus()
                    speaker.speak("Email list")
                    return True
            else:
                # Move to commands by default
                self.back_to_list_btn.SetFocus()
                speaker.speak("Commands")
                return True
        return False

    def on_download_attachment(self, event):
        if not self.current_attachments:
            speaker.speak("No attachments")
            return

        idx = self.attach_list.GetSelection()
        if idx == wx.NOT_FOUND:
            speaker.speak("No attachment selected")
            return

        if self.attach_list.GetString(idx) == "No attachments":
            speaker.speak("No attachments")
            return

        att = self.current_attachments[idx]
        filename = att.get("filename", "attachment")
        data = att.get("data")
        if not data:
            speaker.speak("Attachment data unavailable")
            return

        with wx.FileDialog(
            self,
            "Save Attachment",
            defaultFile=filename,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
            progress = None
            dialog = None
            try:
                progress = AudibleProgress("Downloading attachment, please wait", interval=6)
                progress.start()
                total = len(data)
                chunk_size = 64 * 1024
                dialog = wx.ProgressDialog(
                    "Downloading Attachment",
                    "Downloading, please wait...",
                    maximum=100,
                    style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME
                )
                cancelled = False
                written = 0
                with open(path, "wb") as f:
                    for i in range(0, total, chunk_size):
                        chunk = data[i:i + chunk_size]
                        f.write(chunk)
                        written += len(chunk)
                        percent = int((written / total) * 100) if total else 100
                        keep_going, _ = dialog.Update(percent)
                        if not keep_going:
                            cancelled = True
                            break
                        wx.YieldIfNeeded()

                if cancelled:
                    try:
                        os.remove(path)
                    except:
                        pass
                    speaker.speak("Download cancelled")
                else:
                    speaker.speak("Download complete")
            except Exception as e:
                logger.error(f"Failed to save attachment: {e}")
                speaker.speak("Failed to save attachment")
            finally:
                if dialog:
                    try:
                        dialog.Destroy()
                    except:
                        pass
                if progress:
                    progress.stop()
            self._update_download_label()

    def _update_download_label(self):
        if not self.current_attachments:
            self.download_btn.SetLabel("Download Attachment")
            return
        idx = self.attach_list.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self.current_attachments):
            self.download_btn.SetLabel("Download Attachment")
            return
        att = self.current_attachments[idx]
        data = att.get("data") or b""
        size_str = self._format_bytes(len(data))
        self.download_btn.SetLabel(f"Download ({size_str})")

    def _format_bytes(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _wrap_html(self, html_body: str) -> str:
        header_html = self._build_header_html()
        normalized_body = html_body if not config.get_bool("normalize_html", True) else self._normalize_html(html_body)
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
          <main role="document">
            {header_html}
            <section aria-label="Message body">
              {normalized_body}
            </section>
          </main>
        </body>
        </html>
        """

    def _wrap_plain(self, text_body: str) -> str:
        safe = html.escape(text_body)
        paragraphs = [f"<p>{p.replace('\\n', '<br>')}</p>" for p in safe.split("\n\n") if p.strip()]
        content = "\n".join(paragraphs) if paragraphs else "<p>(No text content)</p>"
        return self._wrap_html(content)

    def _normalize_html(self, html_body: str) -> str:
        """
        Ensure semantic structure for screen readers.
        If content lacks headings/lists, fall back to a normalized text-based layout.
        """
        if not html_body:
            return "<p>(No content)</p>"

        lowered = html_body.lower()
        has_semantics = any(tag in lowered for tag in ["<h1", "<h2", "<h3", "<h4", "<h5", "<h6", "<ul", "<ol", "<li", "<article", "<section>"])
        if has_semantics:
            return html_body

        # Remove script/style blocks
        cleaned = html_body
        for tag in ["script", "style"]:
            while True:
                start = cleaned.lower().find(f"<{tag}")
                if start == -1:
                    break
                end = cleaned.lower().find(f"</{tag}>", start)
                if end == -1:
                    cleaned = cleaned[:start]
                    break
                cleaned = cleaned[:start] + cleaned[end + len(tag) + 3 :]

        # Convert links to text (label and URL)
        def replace_anchor(match):
            text = match.group(2) or ""
            href = match.group(1) or ""
            safe_text = html.escape(text)
            safe_href = html.escape(href)
            if safe_text and safe_href:
                return f"{safe_text} ({safe_href})"
            return safe_text or safe_href

        import re
        cleaned = re.sub(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", replace_anchor, cleaned, flags=re.IGNORECASE | re.DOTALL)

        # Strip remaining tags
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        cleaned = html.unescape(cleaned)

        # Normalize whitespace
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in cleaned.split("\n")]

        # Build semantic blocks with list detection
        blocks = []
        current_paragraph = []
        current_list = []

        def flush_paragraph():
            if current_paragraph:
                text = " ".join(current_paragraph).strip()
                if text:
                    blocks.append(f"<p>{html.escape(text)}</p>")
                current_paragraph.clear()

        def flush_list():
            if current_list:
                items = "".join([f"<li>{html.escape(item)}</li>" for item in current_list])
                blocks.append(f"<ul>{items}</ul>")
                current_list.clear()

        for line in lines:
            if not line:
                flush_paragraph()
                flush_list()
                continue
            list_match = re.match(r"^(\*|-|\d+\\.)\\s+(.*)$", line)
            if list_match:
                flush_paragraph()
                current_list.append(list_match.group(2).strip())
            else:
                flush_list()
                current_paragraph.append(line)

        flush_paragraph()
        flush_list()

        return "\n".join(blocks) if blocks else "<p>(No content)</p>"

    def _build_header_html(self) -> str:
        subject = self.current_headers.get("Subject", "") or (self.current_email or {}).get("subject", "")
        sender = self.current_headers.get("From", "") or (self.current_email or {}).get("sender", "")
        to = self.current_headers.get("To", "")
        cc = self.current_headers.get("Cc", "")
        date = self.current_headers.get("Date", "") or (self.current_email or {}).get("date", "")

        def row(label, value):
            if not value:
                return ""
            return f"<div><strong>{html.escape(label)}:</strong> {html.escape(str(value))}</div>"

        rows = [
            row("From", sender),
            row("To", to),
            row("Cc", cc),
            row("Date", date),
        ]
        rows_html = "\n".join([r for r in rows if r])

        return f"""
        <header aria-label="Message header">
          <h1>{html.escape(subject)}</h1>
          {rows_html}
          <hr>
        </header>
        """

    def _get_top_frame(self):
        return wx.GetTopLevelParent(self)

    def _current_account_email(self):
        if self.current_email:
            return self.current_email.get("account")
        return None

    def on_reply(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "on_reply"):
            top.on_reply(None)
            speaker.speak("Reply")

    def on_forward(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "on_forward"):
            top.on_forward(None)
            speaker.speak("Forward")

    def on_reply_all(self, event):
        if not self.current_email:
            speaker.speak("No email selected")
            return

        account_email = self._current_account_email()
        sender = self.current_headers.get("From") or self.current_email.get("sender", "")
        subject = self.current_headers.get("Subject") or self.current_email.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = "Re: " + subject

        to_addrs = []
        cc_addrs = []
        if self.current_headers.get("To"):
            to_addrs = [addr for name, addr in getaddresses([self.current_headers.get("To")]) if addr]
        if self.current_headers.get("Cc"):
            cc_addrs = [addr for name, addr in getaddresses([self.current_headers.get("Cc")]) if addr]

        all_recipients = []
        # Include original sender
        sender_addr = [addr for name, addr in getaddresses([sender]) if addr]
        all_recipients.extend(sender_addr)
        all_recipients.extend(to_addrs)
        all_recipients.extend(cc_addrs)

        # Remove current account from recipients
        if account_email:
            all_recipients = [r for r in all_recipients if r.lower() != account_email.lower()]

        recipients = ", ".join(sorted(set(all_recipients)))

        from ..dialogs.compose import ComposeDialog
        top = self._get_top_frame()
        parent = top or self
        dialog = ComposeDialog(parent, account_email=account_email, initial_to=recipients, initial_subject=subject, compose_mode="reply")
        dialog.ShowModal()
        dialog.Destroy()
        speaker.speak("Reply all")

    def on_delete(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "email_list_panel"):
            top.email_list_panel.delete_selected()

    def on_archive(self, event):
        top = self._get_top_frame()
        if top and hasattr(top, "email_list_panel"):
            top.email_list_panel.archive_selected()

    def on_toggle_read(self, event):
        top = self._get_top_frame()
        if not top or not hasattr(top, "email_list_panel"):
            return

        panel = top.email_list_panel
        if not panel.repository:
            speaker.speak("No active email connection")
            return
        idx = panel.list.GetFirstSelected()
        if idx == -1:
            speaker.speak("No email selected")
            return

        email_obj = panel.current_view_emails[idx]
        uid = email_obj.get("uid")
        flags = email_obj.get("flags", [])
        is_read = "\\Seen" in flags

        folder_name = panel.current_folder or (self.current_email or {}).get("folder")

        if is_read:
            success = panel.repository.remove_flags([uid], ["\\Seen"], folder_name=folder_name)
            if success:
                email_obj["flags"] = [f for f in flags if f != "\\Seen"]
                speaker.speak("Marked as unread")
        else:
            success = panel.repository.add_flags([uid], ["\\Seen"], folder_name=folder_name)
            if success:
                if "\\Seen" not in flags:
                    flags.append("\\Seen")
                email_obj["flags"] = flags
                speaker.speak("Marked as read")

        panel.refresh_list()
