
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
import os
from ..core.account_manager import AccountManager

logger = logging.getLogger(__name__)

class SMTPClient:
    def __init__(self, account_email: str):
        self.email = account_email
        self.account_manager = AccountManager()

    def send_email(self, to_addrs: list, subject: str, body: str, 
                   cc_addrs: list = None, bcc_addrs: list = None, 
                   attachments: list = None, html: bool = False) -> bool:
        """
        Send an email.
        """
        accounts = self.account_manager.get_accounts()
        account = next((a for a in accounts if a['email'] == self.email), None)

        if not account:
            logger.error(f"Account {self.email} not found.")
            return False

        password = self.account_manager.get_password(self.email)
        if not password:
            logger.error(f"No password found for {self.email}")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = ", ".join(to_addrs)
            msg['Subject'] = subject
            if cc_addrs:
                msg['Cc'] = ", ".join(cc_addrs)

            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {os.path.basename(filepath)}",
                        )
                        msg.attach(part)
                    else:
                        logger.warning(f"Attachment not found: {filepath}")

            # Combine all recipients
            all_recipients = to_addrs + (cc_addrs or []) + (bcc_addrs or [])

            # Connect and send
            if account['smtp_port'] == 587:
                server = smtplib.SMTP(account['smtp_host'], account['smtp_port'])
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(account['smtp_host'], account['smtp_port'])
            
            server.login(self.email, password)
            server.sendmail(self.email, all_recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {all_recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email from {self.email}: {e}")
            return False
