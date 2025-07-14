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
from app.data_processor import DataProcessor # Yeni import

# Konsol ve sensör yöneticisi nesneleri
console = Console()
sensor_manager = SensorManager() # Program başında bir kez oluşturulur
data_processor = DataProcessor() # Program başında bir kez oluşturulur

# ==============================================================================
# Görev Fonksiyonları
# ==============================================================================

def collection_cycle_task():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(
        f"\n[bold yellow]🔄 ({timestamp}) [cyan]Ana Veri Toplama Döngüsü[/cyan] tetiklendi.[/bold yellow]"
    )
    
    # Adım 1: Sensörlerden ham veriyi oku
    console.print("   [dim]...sensörlerden veri okunuyor...[/dim]")
    raw_data = sensor_manager.read_all_sensors()
    console.print(f"   [dim]Ham Veri: {raw_data}[/dim]")

    # Adım 2: Ham veriyi işle
    console.print("   [dim]...veriler işleniyor ve hesaplanıyor...[/dim]")
    processed_data = data_processor.process(raw_data)

    # Adım 3: İşlenmiş veriyi göster
    console.print("\n   [bold green]📊 İşlenmiş Veriler:[/bold green]")
    console.print(f"   🌡️  Sıcaklık: {processed_data['temperature_c']:.2f}°C" if processed_data['temperature_c'] is not None else "   🌡️  Sıcaklık: N/A")
    console.print(f"   💧  Nem: {processed_data['humidity_percent']:.1f}%" if processed_data['humidity_percent'] is not None else "   💧  Nem: N/A")
    console.print(f"   ❄️  Kar Yüksekliği: {processed_data['snow_height_mm']:.1f} mm" if processed_data['snow_height_mm'] is not None else "   ❄️  Kar Yüksekliği: N/A")
    console.print(f"   ⚖️  Kar Ağırlığı: {processed_data['snow_weight_kg']:.2f} kg" if processed_data['snow_weight_kg'] is not None else "   ⚖️  Kar Ağırlığı: N/A")
    console.print(f"   🧱  Kar Yoğunluğu: {processed_data['snow_density_kg_m3']:.1f} kg/m³" if processed_data['snow_density_kg_m3'] is not None else "   🧱  Kar Yoğunluğu: N/A")
    console.print(f"   💧💧 Kar Su Eşdeğeri (SWE): {processed_data['swe_mm']:.1f} mm" if processed_data['swe_mm'] is not None else "   💧💧 Kar Su Eşdeğeri (SWE): N/A")
    console.print(f"   ℹ️  Veri Kaynağı: {processed_data['data_source']}")

    # >>> GELECEK ADIMLAR: Bu işlenmiş veriyi veritabanına kaydetmek <<<


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
        # Başlangıç Paneli
        console.print(
            Panel(
                f"[bold]İstasyon ID:[/] [cyan]{settings.station.id}[/]\n"
                f"[bold]Veri Toplama Aralığı:[/] [cyan]{settings.scheduler.collection_interval_minutes} dakika[/]",
                title="[bold green]❄️  Akıllı Kar İstasyonu Başlatıldı ❄️[/bold green]",
                border_style="green"
            )
        )
        
        scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        
        # Görevleri ekle
        scheduler.add_job(collection_cycle_task, 'interval', minutes=settings.scheduler.collection_interval_minutes, id='collection_task')
        scheduler.add_job(api_and_summary_task, 'cron', hour=settings.scheduler.api_summary_hour, minute=1, id='api_task')
        scheduler.add_job(maintenance_and_retry_task, 'interval', minutes=settings.scheduler.maintenance_interval_minutes, id='maintenance_task')
        
        # Artık başlangıçta manuel çağırmıyoruz, zamanlayıcının ilk döngüsünü bekliyoruz.
        console.print("\n[bold yellow]⏰ Zamanlayıcı kuruldu. İlk döngünün tetiklenmesi bekleniyor...[/bold yellow]")
        console.print("[dim](Çıkmak için Ctrl+C'ye basın)[/dim]\n")
        
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        pass # Sonlandırma mesajı finally bloğunda
    finally:
        # Program kapanırken sadece kalıcı bağlantıları kapat
        sensor_manager.close_all()
        console.print("\n[bold red]🚫 Program sonlandırıldı.[/bold red]")


if __name__ == "__main__":
    main()