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
from app.email_notifier import EmailNotifier
from app.health_monitor import HealthMonitor

# ==============================================================================
# Global Nesneler ve Başlatma
# ==============================================================================

console = Console()
sensor_manager = SensorManager()
data_processor = DataProcessor()
api_client = ApiClient()
anomaly_detector = AnomalyDetector()
report_generator = ReportGenerator()
email_notifier = EmailNotifier()
health_monitor = HealthMonitor()

# ==============================================================================
# Yardımcı Fonksiyonlar
# ==============================================================================

def calculate_summary(readings):
    """Verilen okuma listesinin ortalamasını hesaplar ve API formatına çevirir."""
    if not readings: return None
    def to_float_or_nan(v): return float(v) if v is not None else np.nan
    temps = np.array([to_float_or_nan(r.temperature_c) for r in readings])
    heights = np.array([to_float_or_nan(r.snow_height_mm) for r in readings])
    humidities = np.array([to_float_or_nan(r.humidity_percent) for r in readings])
    
    return {
        "tarih": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "sicaklik": int(round(np.nanmean(temps))) if not np.all(np.isnan(temps)) else 0,
        "nem": int(round(np.nanmean(humidities))) if not np.all(np.isnan(humidities)) else 0,
        "karyuksekligi": int(round(np.nanmean(heights))) if not np.all(np.isnan(heights)) else 0,
    }

# ==============================================================================
# Zamanlanmış Görev Fonksiyonları
# ==============================================================================

def collection_cycle_task():
    """Ana veri toplama, işleme, kaydetme ve anomali kontrolü döngüsü."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[yellow]🔄 ({ts}) [cyan]Ana Veri Toplama Döngüsü[/cyan] tetiklendi.[/yellow]")
    raw_data = sensor_manager.read_all_sensors()
    processed_data = data_processor.process(raw_data)
    storage_manager.save_reading(processed_data)
    anomaly_detector.check(processed_data)
    
    # EKSİK OLAN KISIM BURADA EKLENDİ
    console.print("\n   [green]📊 İşlenmiş Veriler:[/green]")
    console.print(f"   🌡️  Sıcaklık: {processed_data['temperature_c']:.2f}°C" if processed_data['temperature_c'] is not None else "   🌡️  Sıcaklık: N/A")
    console.print(f"   💧  Nem: {processed_data['humidity_percent']:.1f}%" if processed_data['humidity_percent'] is not None else "   💧  Nem: N/A")
    console.print(f"   ❄️  Kar Yüksekliği: {processed_data['snow_height_mm']:.1f} mm")
    console.print(f"   ⚖️  Kar Ağırlığı: {processed_data['snow_weight_kg']:.2f} kg")
    console.print(f"   🧱  Kar Yoğunluğu: {processed_data['snow_density_kg_m3']:.1f} kg/m³")
    console.print(f"   💧💧 Kar Su Eşdeğeri (SWE): {processed_data['swe_mm']:.1f} mm")
    console.print(f"   ℹ️  Veri Kaynağı: {processed_data['data_source']}")


def api_and_summary_task():
    """Saatlik özet alıp API'ye gönderen görev."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[blue]🛰️  ({ts}) [cyan]Saatlik API Gönderim Görevi[/cyan] tetiklendi.[/blue]")
    readings = storage_manager.get_readings_for_last_hour()
    if not readings:
        console.print("  [dim]ℹ️  Son 1 saatte özetlenecek veri bulunamadı.[/dim]")
        return
    summary_payload = calculate_summary(readings)
    if not summary_payload:
        console.print("  [red]❌ Özet verisi oluşturulamadı.[/red]")
        return
    if not api_client.send_hourly_summary(summary_payload):
        storage_manager.add_to_api_queue(json.dumps(summary_payload))

def maintenance_and_retry_task():
    """Bakım, API kuyruğu ve sistem sağlığı kontrol görevleri."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[magenta]🛠️  ({ts}) [cyan]Bakım Görevi[/cyan] tetiklendi.[/magenta]")
    
    # API kuyruğunu işle
    item = storage_manager.get_oldest_from_api_queue()
    if item:
        console.print(f"  [yellow]ℹ️ API kuyruğunda veri bulundu (ID: {item.id}). Tekrar deneniyor...[/yellow]")
        try:
            if api_client.send_hourly_summary(json.loads(item.payload)):
                storage_manager.remove_from_api_queue(item.id)
                console.print(f"  [green]✅ Kuyruktaki veri (ID: {item.id}) gönderildi ve silindi.[/green]")
        except json.JSONDecodeError:
            console.print(f"  [red]❌ Kuyruktaki veri (ID: {item.id}) bozuk. Siliniyor...[/red]")
            storage_manager.remove_from_api_queue(item.id)
    else:
        console.print("  [green]✅ API gönderim kuyruğu boş.[/green]")
        
    # Sistem sağlığını logla
    console.print("  [dim]🩺 Sistem sağlığı loglanıyor...[/dim]")
    health_monitor.log_health_metrics()

def daily_report_task():
    """Her gün sonunda Z Raporu oluşturan görev."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"\n[green]📜 ({ts}) [cyan]Günlük Raporlama Görevi[/cyan] tetiklendi.[/green]")
    report_generator.generate_daily_z_report()

# ==============================================================================
# Ana Program Başlangıç Noktası
# ==============================================================================

def main():
    """Ana program başlangıç noktası. Zamanlayıcıyı kurar ve çalıştırır."""
    try:
        email_notifier.send_email(
            subject="İstasyon Başlatıldı", 
            body=f"Kar Gözlem İstasyonu ({settings.station.id}) {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} tarihinde başarıyla başlatıldı.",
            is_critical=True
        )
        console.print(Panel(f"[bold]İstasyon ID:[/] [cyan]{settings.station.id}[/]", title="[bold green]❄️ Akıllı Kar İstasyonu Başlatıldı ❄️[/bold green]"))
        
        scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        
        # JITTER EKLEMESİ: Görevlerin tam olarak aynı anda başlamasını engeller
        # Her görev 0-15 saniye arası rastgele bir gecikmeyle başlar.
        scheduler.add_job(collection_cycle_task, 'interval', minutes=settings.scheduler.collection_interval_minutes, id='collection_task', jitter=15)
        scheduler.add_job(api_and_summary_task, 'cron', hour=settings.scheduler.api_summary_hour, minute=1, id='api_task')
        scheduler.add_job(maintenance_and_retry_task, 'interval', minutes=settings.scheduler.maintenance_interval_minutes, id='maintenance_task', jitter=15)
        scheduler.add_job(daily_report_task, 'cron', hour=23, minute=55, id='report_task')
        
        console.print("\n[yellow]⏰ Zamanlayıcı kuruldu. İlk döngünün tetiklenmesi bekleniyor...[/yellow]")
        console.print("[dim](Çıkmak için Ctrl+C'ye basın)[/dim]\n")
        
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sensor_manager.close_all()
        console.print("\n[red]🚫 Program sonlandırıldı.[/red]")

if __name__ == "__main__":
    main()