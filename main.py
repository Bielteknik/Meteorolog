# main.py (güncellenmiş hali)
import time
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from rich.console import Console
from rich.panel import Panel

# Değişen importlar
from app.config import settings
from app.storage_manager import storage_manager
from app.sensor_manager import SensorManager # Yeni modül

# Konsol ve sensör yöneticisi nesneleri
console = Console()
sensor_manager = SensorManager() # Program başında bir kez oluşturulur

# ==============================================================================
# Görev Fonksiyonları
# ==============================================================================

def collection_cycle_task():
    """
    Ana veri toplama döngüsünü çalıştıran görev.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"[bold yellow]🔄 ({timestamp}) [cyan]Ana Veri Toplama Döngüsü[/cyan] tetiklendi.[/bold yellow]"
    )
    
    # Adım 1: Sensörlerden ham veriyi oku
    console.print("   [dim]...sensörlerden veri okunuyor...[/dim]")
    raw_data = sensor_manager.read_all_sensors()
    
    # Okunan ham veriyi göster
    console.print("   [bold]Okunan Ham Veriler:[/bold]")
    console.print(f"   📏 Yükseklik: {raw_data['height_raw']}")
    console.print(f"   ⚖️ Ağırlık: {raw_data['weight_raw']}")
    
    # Sıcaklık/Nem verisini formatla
    if raw_data['temp_hum_raw']:
        temp, hum = raw_data['temp_hum_raw']
        console.print(f"   🌡️ Sıcaklık/Nem: {temp:.2f}°C, {hum:.2f}%")
    else:
        console.print("   🌡️ Sıcaklık/Nem: Veri okunamadı.")
    
    # >>> GELECEK ADIMLAR: Veri işleme, kaydetme vb. buraya gelecek <<<


# ... (api_and_summary_task ve maintenance_and_retry_task şimdilik aynı kalabilir) ...
def api_and_summary_task():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"🛰️  ({timestamp}) [cyan]Saatlik API Gönderim Görevi[/cyan] tetiklendi.")

def maintenance_and_retry_task():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"🛠️  ({timestamp}) [cyan]Bakım Görevi[/cyan] tetiklendi.")

# ==============================================================================
# Ana Program
# ==============================================================================

def main():
    try:
        console.print(
            Panel(
                f"[bold]İstasyon ID:[/] [cyan]{settings.station.id}[/]\n"
                f"[bold]Veri Toplama Aralığı:[/] [cyan]{settings.scheduler.collection_interval_minutes} dakika[/]",
                title="[bold green]❄️ Akıllı Kar İstasyonu Başlatıldı ❄️[/bold green]",
                border_style="green"
            )
        )
        
        scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        
        # Görevleri ekle
        scheduler.add_job(collection_cycle_task, 'interval', minutes=settings.scheduler.collection_interval_minutes)
        scheduler.add_job(api_and_summary_task, 'cron', hour=settings.scheduler.api_summary_hour, minute=1) # 0 çakışmasın diye 1 yapalım
        scheduler.add_job(maintenance_and_retry_task, 'interval', minutes=settings.scheduler.maintenance_interval_minutes)
        
        console.print("\n[bold yellow]⏰ Zamanlayıcı kuruldu. İlk döngü hemen çalıştırılıyor...[/bold yellow]")
        # Program başlar başlamaz ilk veriyi almak için görevi bir kere manuel çağır
        collection_cycle_task()
        
        console.print("\n[bold yellow]✅ İlk döngü tamamlandı. Normal zamanlama bekleniyor...[/bold yellow]")
        console.print("[dim](Çıkmak için Ctrl+C'ye basın)[/dim]\n")
        
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        console.print("\n[bold red]🚫 Program sonlandırılıyor...[/bold red]")
    finally:
        # Program kapanırken sadece kalıcı bağlantıları kapat
        sensor_manager.close_all()
        console.print("\n[bold red]🚫 Program sonlandırıldı.[/bold red]")

if __name__ == "__main__":
    main()