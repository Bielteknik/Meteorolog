import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from app.config import settings

class NotificationService:
    """E-posta ile bildirim gönderme servisi."""
    def __init__(self):
        if not settings.EMAIL_ENABLED:
            self.enabled = False
            return

        self.enabled = True
        self.smtp_server = settings.EMAIL_SMTP_SERVER
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.sender_email = settings.EMAIL_SENDER
        self.sender_password = settings.EMAIL_PASSWORD
        self.recipient_email = settings.EMAIL_RECIPIENT
        self.hostname = socket.gethostname()

    def _send_email(self, subject: str, message: str) -> bool:
        """E-posta gönderme işleminin çekirdeği."""
        if not self.enabled:
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
            print(f"✅ E-posta gönderildi: {subject}")
            return True
        except Exception as e:
            print(f"❌ E-posta gönderme hatası: {e}")
            return False

    def send_startup_notification(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = "Meteoroloji Servisi Başlatıldı"
        message = f"Sistem başlatıldı.\n\nZaman: {timestamp}\nSunucu: {self.hostname}"
        return self._send_email(subject, message)
    
    def send_error_notification(self, error_title: str, error_details: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"Meteoroloji Servis Hatası: {error_title}"
        message = f"Sistemde bir hata oluştu.\n\nZaman: {timestamp}\nSunucu: {self.hostname}\nHata: {error_title}\n\nDetaylar:\n{error_details}"
        return self._send_email(subject, message)