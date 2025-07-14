import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from .config import settings
from .storage_manager import storage_manager

class EmailNotifier:
    """E-posta ile bildirim gönderme işlemlerini yönetir."""

    def _can_send_email(self) -> bool:
        """E-posta gönderme limitinin aşılıp aşılmadığını kontrol eder."""
        if not settings.email.enabled:
            return False
        
        session = storage_manager.get_session()
        try:
            one_day_ago = datetime.now() - timedelta(hours=24)
            sent_today = session.query(EmailLog).filter(EmailLog.timestamp >= one_day_ago).count()
            
            if sent_today >= settings.email.daily_limit:
                print(f"  ⚠️ Günlük e-posta limiti ({settings.email.daily_limit}) aşıldı. E-posta gönderilmeyecek.")
                return False
            return True
        finally:
            session.close()

    def _log_email(self, subject: str):
        """Gönderilen e-postayı veritabanına kaydeder."""
        session = storage_manager.get_session()
        try:
            log = EmailLog(recipient=settings.email.recipient, subject=subject)
            session.add(log)
            session.commit()
        finally:
            session.close()

    def send_email(self, subject: str, body: str, is_critical: bool = False):
        """
        Belirtilen konu ve içerikle e-posta gönderir.
        is_critical=True ise e-posta limitini yok sayar.
        """
        if not settings.email.enabled:
            print("  ℹ️ E-posta gönderimi devre dışı.")
            return

        if not is_critical and not self._can_send_email():
            return

        print(f"  📧 E-posta gönderiliyor: '{subject}'")
        
        msg = MIMEMultipart()
        msg['From'] = settings.email.sender
        msg['To'] = settings.email.recipient
        msg['Subject'] = f"[{settings.station.id}] - {subject}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            # SSL/TLS için SMTPServer nesnesi
            server = smtplib.SMTP_SSL(settings.email.smtp_server, settings.email.smtp_port)
            server.login(settings.email.sender, settings.secrets.password)
            server.send_message(msg)
            server.quit()
            
            print("  ✅ E-posta başarıyla gönderildi.")
            self._log_email(subject) # Gönderimi logla
        except Exception as e:
            print(f"  ❌ E-posta gönderme hatası: {e}")