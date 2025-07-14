import time
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from rich.console import Console
from rich.panel import Panel

# Değişiklik burada:
from app.config import settings
from app.storage_manager import storage_manager # Yeni modülü import et

# Konsol nesnesini oluştur
console = Console()

# ==============================================================================
# Görev Fonksiyonları (Şimdilik Boş)
# ==============================================================================

def collection_cycle_task():
    """
    Ana veri toplama döngüsünü çalıştıran görev.
    Bu görev, config'deki 'collection_interval_minutes' aralığıyla çalışır.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"[bold yellow]🔄 ({timestamp}) [cyan]Ana Veri Toplama Döngüsü[/cyan] tetiklendi.[/bold yellow]"
    )
    # >>> BURAYA GELECEKTE SENSÖR OKUMA VE İŞLEME KODLARI GELECEK <<<
    console.print("   [dim]...veri toplanıyor, işleniyor, kaydediliyor...[/dim]")


def api_and_summary_task():
    """
    Saatlik özet alıp API'ye gönderen görev.
    Bu görev, her saat başı çalışır.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"[bold blue]🛰️  ({timestamp}) [cyan]Saatlik API Gönderim Görevi[/cyan] tetiklendi.[/bold blue]"
    )
    # >>> BURAYA GELECEKTE VERİTABANINDAN ORTALAMA ALMA VE API'YE GÖNDERME KODU GELECEK <<<


def maintenance_and_retry_task():
    """
    Bakım ve yeniden deneme görevlerini çalıştıran görev.
    Bu görev, config'deki 'maintenance_interval_minutes' aralığıyla çalışır.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"[bold magenta]🛠️  ({timestamp}) [cyan]Bakım Görevi[/cyan] tetiklendi.[/bold magenta]"
    )
    # >>> BURAYA GELECEKTE API KUYRUĞU VE SENSÖR SAĞLIĞI KONTROL KODLARI GELECEK <<<

# ==============================================================================
# Ana Program
# ==============================================================================

def main():
    """
    Ana program başlangıç noktası.
    Zamanlayıcıyı kurar ve çalıştırır.
    """
    try:
        # Başlangıç Paneli
        console.print(
            Panel(
                f"[bold]İstasyon ID:[/] [cyan]{settings.station.id}[/]\n"
                f"[bold]Veri Toplama Aralığı:[/] [cyan]{settings.scheduler.collection_interval_minutes} dakika[/]\n"
                f"[bold]API Gönderim:[/] [cyan]Her saat başı[/]",
                title="[bold green]❄️ Akıllı Kar İstasyonu Başlatıldı ❄️[/bold green]",
                border_style="green"
            )
        )
        
        # Zamanlayıcıyı kur
        scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        
        # Görevleri zamanlayıcıya ekle
        scheduler.add_job(
            collection_cycle_task,
            'interval',
            minutes=settings.scheduler.collection_interval_minutes,
            id='collection_task'
        )
        
        scheduler.add_job(
            api_and_summary_task,
            'cron',
            hour=settings.scheduler.api_summary_hour,
            minute=0, # Her saatin 0. dakikasında
            id='api_task'
        )
        
        scheduler.add_job(
            maintenance_and_retry_task,
            'interval',
            minutes=settings.scheduler.maintenance_interval_minutes,
            id='maintenance_task'
        )
        
        console.print("[bold yellow]⏰ Zamanlayıcı kuruldu. Görevlerin tetiklenmesi bekleniyor...[/bold yellow]")
        console.print("[dim](Çıkmak için Ctrl+C'ye basın)[/dim]\n")
        
        # Zamanlayıcıyı başlat (bu satır programı burada kilitler ve görevleri çalıştırır)
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        console.print("\n[bold red]🚫 Program sonlandırılıyor...[/bold red]")
    except Exception as e:
        console.print(f"[bold red]💥 Beklenmedik bir hata oluştu: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()