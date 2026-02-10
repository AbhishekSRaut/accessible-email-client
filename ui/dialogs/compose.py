
import wx
import logging
import html
from ...core.account_manager import AccountManager
from ...core.smtp_client import SMTPClient
from ...core.configuration import config
from ...utils.accessibility import speaker
from ...utils.accessible_widgets import AccessibleTextCtrl, AccessibleButton, AccessibleListBox

logger = logging.getLogger(__name__)

class ComposeDialog(wx.Dialog):
    def __init__(self, parent, account_email=None, initial_to="", initial_subject="", initial_body="", compose_mode="new"):
        super().__init__(parent, title="Compose New Email", size=(600, 500))
        self.account_manager = AccountManager()
        self.account_email = account_email
        self.initial_to = initial_to
        self.initial_subject = initial_subject
        self.initial_body = initial_body
        self.compose_mode = compose_mode
        self.attachments = []
        self.signature_meta = None
        
        if not self.account_email:
            # Default to first account if available
            accounts = self.account_manager.get_accounts()
            if accounts:
                self.account_email = accounts[0]['email']
        
        self.init_ui()
        self.apply_signature()
        self.Center()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        
        # Initial focus
        if self.account_email:
            if not self.initial_to:
                self.to_input.SetFocus()
            elif not self.initial_body:
                self.body_input.SetFocus()
            else:
                 self.body_input.SetInsertionPoint(0)
                 self.body_input.SetFocus()
        else:
            wx.MessageBox("No accounts configured. Please add an account first.", "Error", wx.OK | wx.ICON_ERROR)
            self.EndModal(wx.ID_CANCEL)

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Grid for headers
        grid = wx.FlexGridSizer(rows=6, cols=2, vgap=10, hgap=10)
        
        # From (Static for now, could be choice)
        grid.Add(wx.StaticText(panel, label="From:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.from_lbl = wx.StaticText(panel, label=self.account_email or "No Account")
        grid.Add(self.from_lbl, 1, wx.EXPAND)
        
        # To
        grid.Add(wx.StaticText(panel, label="To:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.to_input = AccessibleTextCtrl(panel, value=self.initial_to)
        self.to_input.init_accessible("To field", "Use comma or semicolon for multiple recipients")
        grid.Add(self.to_input, 1, wx.EXPAND)
        
        # Cc
        grid.Add(wx.StaticText(panel, label="Cc:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cc_input = AccessibleTextCtrl(panel, value="")
        self.cc_input.init_accessible("Cc field", "Use comma or semicolon for multiple recipients")
        grid.Add(self.cc_input, 1, wx.EXPAND)

        # Bcc
        grid.Add(wx.StaticText(panel, label="Bcc:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.bcc_input = AccessibleTextCtrl(panel, value="")
        self.bcc_input.init_accessible("Bcc field", "Use comma or semicolon for multiple recipients")
        grid.Add(self.bcc_input, 1, wx.EXPAND)

        # Subject
        grid.Add(wx.StaticText(panel, label="Subject:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.subject_input = AccessibleTextCtrl(panel, value=self.initial_subject)
        self.subject_input.init_accessible("Subject field")
        grid.Add(self.subject_input, 1, wx.EXPAND)
        
        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 0, wx.EXPAND | wx.ALL, 10)
        
        # Recipient hint
        hint = wx.StaticText(panel, label="Use comma or semicolon to separate multiple recipients in To, Cc, or Bcc.")
        vbox.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Attachments
        attach_label = wx.StaticText(panel, label="Attachments:")
        vbox.Add(attach_label, 0, wx.LEFT | wx.RIGHT, 10)

        attach_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.attach_list = AccessibleListBox(panel, choices=[])
        self.attach_list.init_accessible("Attachments list", "Select an attachment to remove")
        attach_sizer.Add(self.attach_list, 1, wx.ALL | wx.EXPAND, 5)

        attach_btns = wx.BoxSizer(wx.VERTICAL)
        self.add_attach_btn = AccessibleButton(panel, label="Add Attachment")
        self.add_attach_btn.init_accessible("Add attachment button", announce=False)
        self.add_attach_btn.Bind(wx.EVT_BUTTON, self.on_add_attachment)
        attach_btns.Add(self.add_attach_btn, 0, wx.ALL, 4)

        self.remove_attach_btn = AccessibleButton(panel, label="Remove Selected")
        self.remove_attach_btn.init_accessible("Remove attachment button", announce=False)
        self.remove_attach_btn.Bind(wx.EVT_BUTTON, self.on_remove_attachment)
        attach_btns.Add(self.remove_attach_btn, 0, wx.ALL, 4)

        attach_sizer.Add(attach_btns, 0, wx.ALL, 5)
        vbox.Add(attach_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # Body
        vbox.Add(wx.StaticText(panel, label="Message Body:"), 0, wx.LEFT | wx.RIGHT, 10)
        self.body_input = AccessibleTextCtrl(panel, style=wx.TE_MULTILINE, value=self.initial_body)
        self.body_input.init_accessible("Message body")
        # Function to move cursor to start if replying
        if self.initial_body:
            self.body_input.SetInsertionPoint(0)
            
        vbox.Add(self.body_input, 1, wx.EXPAND | wx.ALL, 10)

        # HTML toggle (optional)
        self.html_checkbox = wx.CheckBox(panel, label="Send as HTML (optional)")
        self.html_checkbox.SetValue(False)
        vbox.Add(self.html_checkbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Buttons
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        self.send_btn = AccessibleButton(panel, label="Send")
        self.send_btn.init_accessible("Send button", announce=False)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send)
        hbox.Add(self.send_btn, 0, wx.RIGHT, 10)
        
        self.cancel_btn = AccessibleButton(panel, label="Cancel")
        self.cancel_btn.init_accessible("Cancel button", announce=False)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        hbox.Add(self.cancel_btn, 0)
        
        vbox.Add(hbox, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        
        panel.SetSizer(vbox)
        
        # Shortcuts
        accel = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, wx.WXK_RETURN, self.send_btn.GetId())
        ])
        self.SetAcceleratorTable(accel)

    def on_send(self, event):
        recipient = self.to_input.GetValue()
        cc_raw = self.cc_input.GetValue()
        bcc_raw = self.bcc_input.GetValue()
        subject = self.subject_input.GetValue()
        body = self.body_input.GetValue()

        if not recipient:
            speaker.speak("Recipient is required")
            wx.MessageBox("Please specify a recipient.", "Error", wx.OK | wx.ICON_ERROR)
            return
            
        speaker.speak("Sending email...")
        progress = None
        try:
            from ...utils.progress import AudibleProgress
            progress = AudibleProgress("Sending email, please wait", interval=6)
            progress.start()
        except:
            progress = None
        
        try:
            client = SMTPClient(self.account_email)
            # Handle multiple recipients if separated by comma/semicolon
            recipients = [r.strip() for r in recipient.replace(';', ',').split(',') if r.strip()]
            cc_list = [r.strip() for r in cc_raw.replace(';', ',').split(',') if r.strip()]
            bcc_list = [r.strip() for r in bcc_raw.replace(';', ',').split(',') if r.strip()]
            
            send_as_html = self.html_checkbox.GetValue()
            if send_as_html:
                body = self._build_html_body(body)
            if client.send_email(recipients, subject, body, cc_addrs=cc_list, bcc_addrs=bcc_list, attachments=self.attachments, html=send_as_html):
                speaker.speak("Email sent successfully")
                wx.MessageBox("Email sent successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
                self.EndModal(wx.ID_OK)
            else:
                speaker.speak("Failed to send email")
                wx.MessageBox("Failed to send email. Check logs.", "Error", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            logger.error(f"Send error: {e}")
            speaker.speak("Error sending email")
            wx.MessageBox(f"Error: {e}", "Error", wx.OK | wx.ICON_ERROR)
        finally:
            if progress:
                progress.stop()

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def on_add_attachment(self, event):
        with wx.FileDialog(
            self,
            "Add Attachments",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            paths = dlg.GetPaths()
            for path in paths:
                if path not in self.attachments:
                    self.attachments.append(path)
            self._refresh_attachments()
            speaker.speak("Attachments added")

    def on_remove_attachment(self, event):
        idx = self.attach_list.GetSelection()
        if idx == wx.NOT_FOUND:
            speaker.speak("No attachment selected")
            return
        if 0 <= idx < len(self.attachments):
            self.attachments.pop(idx)
            self._refresh_attachments()
            speaker.speak("Attachment removed")

    def _refresh_attachments(self):
        self.attach_list.Clear()
        for path in self.attachments:
            name = path.split("\\")[-1]
            self.attach_list.Append(name)
        if self.attach_list.GetCount() > 0:
            self.attach_list.SetSelection(0)

    def apply_signature(self):
        prefs = config.get("signature_prefs", {})
        account_key = (self.account_email or "").lower()
        acc_prefs = (prefs.get("accounts") or {}).get(account_key, {})
        global_prefs = prefs.get("global", {})

        sig = acc_prefs if acc_prefs else global_prefs
        if not sig:
            return

        enabled = bool(sig.get("enabled", False))
        apply_to = sig.get("apply_to") or {}
        if not enabled:
            return

        if not apply_to.get(self.compose_mode, False):
            return

        signature_text = sig.get("text") or ""
        signature_html = sig.get("html") or ""
        use_html = bool(sig.get("use_html", False))
        position = sig.get("position", "bottom")
        separator = bool(sig.get("separator", True))

        sig_block = signature_text
        if signature_text:
            if separator:
                sig_block = "-- \n" + signature_text
            body = self.body_input.GetValue()
            if position == "top":
                body = f"{sig_block}\n\n{body}".strip()
            else:
                if body:
                    body = body.rstrip()
                    body = f"{body}\n\n{sig_block}"
                else:
                    body = sig_block
            self.body_input.SetValue(body)

        self.signature_meta = {
            "text": signature_text,
            "html": signature_html,
            "use_html": use_html,
            "position": position,
            "separator": separator
        }

        if use_html:
            self.html_checkbox.SetValue(True)

    def _build_html_body(self, body_text: str) -> str:
        meta = self.signature_meta or {}
        sig_text = meta.get("text") or ""
        sig_html = meta.get("html") or ""
        separator = bool(meta.get("separator", True))

        # If signature text exists and is at the end, remove it to replace with HTML signature
        if sig_text:
            sig_block = f"-- \n{sig_text}" if separator else sig_text
            trimmed = body_text.rstrip()
            if trimmed.endswith(sig_block):
                trimmed = trimmed[: -len(sig_block)].rstrip()
                body_text = trimmed

        html_body = self._text_to_html(body_text)

        if meta.get("use_html") and sig_html:
            if meta.get("position", "bottom") == "top":
                html_body = f"{sig_html}\n{html_body}"
            else:
                html_body = f"{html_body}\n{sig_html}"

        return html_body

    def _text_to_html(self, text_body: str) -> str:
        safe = html.escape(text_body or "")
        paragraphs = [f"<p>{p.replace('\\n', '<br>')}</p>" for p in safe.split("\n\n") if p.strip()]
        return "\n".join(paragraphs) if paragraphs else "<p>(No content)</p>"
