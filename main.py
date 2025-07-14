import time
import sys
import json
import numpy as np
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from rich.console import Console
from rich.panel import Panel

# Proje içi modülleri import et
from app.config import settings
from app.storage_manager import storage_manager
from app.sensor_manager import SensorManager
from app.data_processor import DataProcessor
from app.weather_api import ApiClient
from app.anomaly_detector import AnomalyDetector
from app.report_generator import ReportGenerator

# ==============================================================================
# Global Nesneler ve Başlatma
# ==============================================================================

console = Console()
sensor_manager = SensorManager()
data_processor = DataProcessor()
api_client = ApiClient()
anomaly_detector = AnomalyDetector()
report_generator = ReportGenerator()

# ==============================================================================
# Yardımcı Fonksiyonlar
# ==============================================================================

def calculate_summary(readings):
    """Verilen okuma listesinin ortalamasını hesaplar ve API formatına çevirir."""
    if not readings:
        return None
    
    def to_float_or_nan(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return np.nan

    temperatures = np.array([to_float_or_nan(r.temperature_c) for r in readings])
    humidities = np.array([to_float_or_nan(r.humidity_percent) for r in readings])
    snow_heights = np.array([to_float_or_nan(r.snow_height_mm) for r in readings])
    
    summary = {
        'temperature_c': np.nanmean(temperatures),
        'humidity_percent': np.nanmean(humidities),
        'snow_height_mm': np.nanmean(snow_heights),
    }
    
    api_payload = {
        "tarih": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "sicaklik": int(round(summary.get('temperature_c', 0))),
        "nem": int(round(summary.get('humidity_percent', 0))),
        "karyuksekligi": int(round(summary.get('snow_height_mm', 0))),
    }
    return api_payload

# ==============================================================================
# Zamanlanmış Görev Fonksiyonları
# ==============================================================================

def collection_cycle_task():
    """Ana veri toplama, işleme, kaydetme ve anomali kontrolü döngüsü."""
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

    # Adım 3: İşlenmiş veriyi veritabanına kaydet
    storage_manager.save_reading(processed_data)

    # Adım 4: Anomali kontrolü yap
    console.print("   [dim]...anomali kontrolü yapılıyor...[/dim]")
    anomaly_detector.check(processed_data)
    
    # Adım 5: İşlenmiş veriyi konsolda göster
    console.print("\n   [bold green]📊 İşlenmiş Veriler:[/bold green]")
    console.print(f"   🌡️  Sıcaklık: {processed_data['temperature_c']:.2f}°C" if processed_data['temperature_c'] is not None else "   🌡️  Sıcaklık: N/A")
    console.print(f"   💧  Nem: {processed_data['humidity_percent']:.1f}%" if processed_data['humidity_percent'] is not None else "   💧  Nem: N/A")
    console.print(f"   ❄️  Kar Yüksekliği: {processed_data['snow_height_mm']:.1f} mm")
    console.print(f"   ⚖️  Kar Ağırlığı: {processed_data['snow_weight_kg']:.2f} kg")
    console.print(f"   🧱  Kar Yoğunluğu: {processed_data['snow_density_kg_m3']:.1f} kg/m³")
    console.print(f"   💧💧 Kar Su Eşdeğeri (SWE): {processed_data['swe_mm']:.1f} mm")
    console.print(f"   ℹ️  Veri Kaynağı: {processed_data['data_source']}")


def api_and_summary_task():
    """Saatlik özet alıp API'ye gönderen görev."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[bold blue]🛰️  ({timestamp}) [cyan]Saatlik API Gönderim Görevi[/cyan] tetiklendi.[/bold blue]")
    
    readings = storage_manager.get_readings_for_last_hour()
    if not readings:
        console.print("  ℹ️  Son 1 saatte özetlenecek veri bulunamadı.")
        return

    summary_payload = calculate_summary(readings)
    if not summary_payload:
        console.print("  ❌ Özet verisi oluşturulamadı.")
        return

    success = api_client.send_hourly_summary(summary_payload)
    if not success:
        storage_manager.add_to_api_queue(json.dumps(summary_payload))


def maintenance_and_retry_task():
    """Bakım ve API kuyruğu kontrol görevlerini çalıştıran görev."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[bold magenta]🛠️  ({timestamp}) [cyan]Bakım ve Kuyruk Kontrol Görevi[/cyan] tetiklendi.[/bold magenta]")
    
    item_from_queue = storage_manager.get_oldest_from_api_queue()
    if item_from_queue:
        console.print(f"  ℹ️ API kuyruğunda bekleyen veri bulundu (ID: {item_from_queue.id}). Tekrar deneniyor...")
        try:
            payload_dict = json.loads(item_from_queue.payload)
            success = api_client.send_hourly_summary(payload_dict)
            if success:
                storage_manager.remove_from_api_queue(item_from_queue.id)
                console.print(f"  ✅ Kuyruktaki veri (ID: {item_from_queue.id}) başarıyla gönderildi ve silindi.")
        except json.JSONDecodeError:
            console.print(f"  ❌ Kuyruktaki veri (ID: {item_from_queue.id}) bozuk (JSON değil). Siliniyor...")
            storage_manager.remove_from_api_queue(item_from_queue.id)
    else:
        console.print("  ✅ API gönderim kuyruğu boş.")


def daily_report_task():
    """Her gün sonunda Z Raporu oluşturan görev."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[bold green]📜 ({timestamp}) [cyan]Günlük Raporlama Görevi[/cyan] tetiklendi.[/bold green]")
    report_generator.generate_daily_z_report()

# ==============================================================================
# Ana Program Başlangıç Noktası
# ==============================================================================

def main():
    """
    Ana program başlangıç noktası.
    Zamanlayıcıyı kurar ve çalıştırır.
    """
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
            minute=1,
            id='api_task'
        )
        
        scheduler.add_job(
            maintenance_and_retry_task,
            'interval',
            minutes=settings.scheduler.maintenance_interval_minutes,
            id='maintenance_task'
        )
        
        scheduler.add_job(
            daily_report_task,
            'cron',
            hour=23,
            minute=55,
            id='report_task'
        )
        
        console.print("\n[bold yellow]⏰ Zamanlayıcı kuruldu. İlk döngünün tetiklenmesi bekleniyor...[/bold yellow]")
        console.print("[dim](Çıkmak için Ctrl+C'ye basın)[/dim]\n")
        
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sensor_manager.close_all()
        console.print("\n[bold red]🚫 Program sonlandırıldı.[/bold red]")

if __name__ == "__main__":
    main()