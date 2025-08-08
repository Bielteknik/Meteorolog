import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from rich.console import Console

# Proje içi modülleri import et
from .config import settings
# Düzeltme: EmailLog modelini de import ediyoruz
from .storage_manager import storage_manager, EmailLog

console = Console()

class EmailNotifier:
    """E-posta ile bildirim gönderme işlemlerini yönetir."""

    def _can_send_email(self) -> bool:
        """E-posta gönderme limitinin aşılıp aşılmadığını kontrol eder."""
        if not settings.email.enabled:
            return False
        
        session = storage_manager.get_session()
        try:
            one_day_ago = datetime.now() - timedelta(hours=24)
            # Sadece kritik olmayan e-postaları say
            sent_today = session.query(EmailLog).filter(
                EmailLog.timestamp >= one_day_ago,
                EmailLog.subject.notlike('%Kritik%') # 'Kritik' içermeyenleri say
            ).count()
            
            if sent_today >= settings.email.daily_limit:
                console.print(f"  [yellow]⚠️ Günlük e-posta limiti ({settings.email.daily_limit}) aşıldı. E-posta gönderilmeyecek.[/yellow]")
                return False
            return True
        finally:
            session.close()

    def _log_email(self, subject: str):
        """Gönderilen e-postayı veritabanına kaydeder."""
        if not settings.email.enabled:
            return
            
        session = storage_manager.get_session()
        try:
            log = EmailLog(recipient=settings.email.recipient, subject=subject)
            session.add(log)
            session.commit()
        except Exception as e:
            console.print(f"  [red]❌ E-posta loglama hatası: {e}[/red]")
            session.rollback()
        finally:
            session.close()

    def send_email(self, subject: str, body: str, is_critical: bool = False):
        """
        Belirtilen konu ve içerikle e-posta gönderir.
        is_critical=True ise e-posta limitini yok sayar.
        """
        if not settings.email.enabled:
            console.print("  [dim]ℹ️ E-posta gönderimi devre dışı.[/dim]")
            return

        if not is_critical and not self._can_send_email():
            return

        final_subject = f"[KRİTİK] - [{settings.station.id}] - {subject}" if is_critical else f"[{settings.station.id}] - {subject}"
        
        console.print(f"  [cyan]📧 E-posta gönderiliyor: '{final_subject}'[/cyan]")
        
        msg = MIMEMultipart()
        msg['From'] = settings.email.sender
        msg['To'] = settings.email.recipient
        msg['Subject'] = final_subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        try:
            # SSL/TLS için SMTPServer nesnesi (Port 465)
            server = smtplib.SMTP_SSL(settings.email.smtp_server, settings.email.smtp_port, timeout=10)
            server.login(settings.email.sender, settings.secrets.password)
            server.send_message(msg)
            server.quit()
            
            console.print("  [green]✅ E-posta başarıyla gönderildi.[/green]")
            self._log_email(final_subject)
        except Exception as e:
            console.print(f"  [red]❌ E-posta gönderme hatası: {e}[/red]")