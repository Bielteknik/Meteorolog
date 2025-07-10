# app/services/notification.py
import smtplib
import socket
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """E-posta ile bildirim gönderme servisi."""
    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED
        self.smtp_server = settings.EMAIL_SMTP_SERVER
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.sender_email = settings.EMAIL_SENDER
        self.sender_password = settings.EMAIL_PASSWORD
        self.recipient_email = settings.EMAIL_RECIPIENT
        try:
            self.hostname = socket.gethostname()
        except Exception:
            self.hostname = "unknown_host"
            logger.warning("Could not determine hostname.")

    def _send_email(self, subject: str, message: str) -> bool:
        """E-posta gönderme işleminin çekirdeği."""
        if not self.enabled:
            logger.debug("Email notifications are disabled. Skipping sending.")
            return False
        
        # DEĞİŞİKLİK: E-posta göndermeden önce ayarların tam olup olmadığını kontrol et
        if not all([self.smtp_server, self.smtp_port, self.sender_email, self.sender_password, self.recipient_email]):
            logger.warning("Email settings are incomplete. Skipping sending email.")
            return False

        try:
            email = MIMEMultipart()
            email["From"] = self.sender_email
            email["To"] = self.recipient_email
            email["Subject"] = f"[{self.hostname}] {subject}"
            email.attach(MIMEText(message, "plain"))

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            server.login(self.sender_email, self.sender_password)
            server.send_message(email)
            server.quit()
            logger.info(f"Email notification sent successfully: '{subject}'")
            return True
        except Exception as e:
            # DEĞİŞİKLİK: Seviye 'error'dan 'warning'e düşürüldü.
            logger.warning(f"Failed to send email notification: {e}", exc_info=False)
            return False

    def send_startup_notification(self):
        """Sistem başlangıcında bildirim gönderir."""
        subject = "Meteoroloji Servisi Başlatıldı"
        message = f"Sistem başlatıldı.\n\nZaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nSunucu: {self.hostname}"
        self._send_email(subject, message)
    
    def send_error_notification(self, error_title: str, error_details: str):
        """Hata durumunda bildirim gönderir."""
        subject = f"Meteoroloji Servis Hatası: {error_title}"
        message = f"Sistemde bir hata oluştu.\n\nZaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nSunucu: {self.hostname}\nHata: {error_title}\n\nDetaylar:\n{error_details}"
        self._send_email(subject, message)