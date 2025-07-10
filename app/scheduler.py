import schedule
import time
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import List, Dict
from tqdm import tqdm
from rich.console import Console
from rich.table import Table

from app.config import settings
from app.models.schemas import ProcessedReading
from app.sensors.manager import SensorManager
from app.core.collector import DataCollector
from app.core.processor import DataProcessor
from app.services.database import DatabaseService
from app.services.storage import CsvStorageService
from app.services.notification import NotificationService
from app.services.remote_api_service import RemoteApiService

logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self):
        # ... Bu kısımda değişiklik yok ...
        self.console = Console()
        self.sensor_manager = SensorManager()
        self.processor = DataProcessor()
        self.collector = DataCollector(self.sensor_manager)
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()
        self.remote_api = RemoteApiService()

    def setup_schedule(self):
        # ... Bu kısımda değişiklik yok ...
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle)
        logger.info(f"Ana görev {interval} dakikada bir çalışacak şekilde ayarlandı.")
        schedule.every().hour.at(":01").do(self.run_remote_post_job)
        logger.info("Uzak API'ye veri gönderme görevi her saatin 1. dakikasında çalışacak şekilde ayarlandı.")

    def run_remote_post_job(self):
        # ... Bu kısımda değişiklik yok ...
        logger.info("Uzak API'ye veri gönderme görevi başlatılıyor...")
        try:
            latest_reading = self.db_service.get_latest_reading()
            if latest_reading: self.remote_api.post_reading(latest_reading)
            else: logger.warning("Uzak API'ye göndermek için veritabanında hiç kayıt bulunamadı.")
        except Exception as e:
            logger.error(f"Uzak API'ye veri gönderme görevinde beklenmedik bir hata oluştu: {e}", exc_info=True)
            self.notification_service.send_error_notification("Uzak API'ye Veri Gönderme Hatası", traceback.format_exc())

    def run_collection_cycle(self):
        logger.info("Veri toplama döngüsü başlatılıyor...")
        cycle_events: List[Dict[str, str]] = []
        burst_anomalies: Dict[str, str] = {}
        try:
            # 1. Bağlan ve Hazırla
            self.sensor_manager.discover_and_connect()
            self.sensor_manager.prepare_for_reading()
            
            # Bağlantı hatalarını olay listesine ekle
            if not self.sensor_manager.is_height_connected:
                cycle_events.append({"category": "📏 Yükseklik Sensörü", "status": "❌ BAŞARISIZ", "detail": "Port bulunamadı."})
            if not self.sensor_manager.is_temp_hum_connected:
                cycle_events.append({"category": "🔌 I2C Sensörü (S/N)", "status": "❌ BAŞARISIZ", "detail": "Bağlantı zaman aşımına uğradı (Kablolama?)."})
                if not self.collector.owm_service.is_fallback_active:
                    self.collector.owm_service.is_fallback_active = True
                    is_updated = self.collector.owm_service.update_cache(force_update=True)
                    if not is_updated:
                         cycle_events.append({"category": "📡 OWM API (Yedek)", "status": "❌ BAŞARISIZ", "detail": "İnternet/DNS sorunu: API'ye ulaşılamadı."})
            else: self.collector.owm_service.is_fallback_active = False

            # 2. Veri Topla
            collected_readings: List[ProcessedReading] = []
            burst_duration = timedelta(minutes=settings.DATA_BURST_DURATION_MINUTES)
            end_time = datetime.now() + burst_duration
            with tqdm(total=int(burst_duration.total_seconds()), desc="[bold magenta]🔥 Veri Toplanıyor[/bold magenta]", bar_format="{l_bar}{bar}|", file=sys.stdout, leave=True) as pbar:
                while datetime.now() < end_time:
                    start_loop_time = time.time()
                    raw_data = self.collector.collect_raw_data()
                    processed_data, anomalies = self.processor.process_single_reading(raw_data)
                    if anomalies: burst_anomalies.update(anomalies)
                    collected_readings.append(processed_data)
                    sleep_time = max(0, settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS - (time.time() - start_loop_time))
                    time.sleep(sleep_time)
                    pbar.update(int(settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS))
            print()

            # 3. Raporlama ve Kaydetme
            for metric, detail in burst_anomalies.items():
                parts = detail.split('|'); anomaly_type = parts[0].strip()
                cycle_events.append({"category": f"{metric} Verisi", "status": "⚠️ ANOMALİ", "detail": detail})

            if cycle_events:
                self._print_cycle_report(cycle_events)
                error_details = "\n".join([f"- {e['category']} ({e['status']}): {e['detail']}" for e in cycle_events])
                self.notification_service.send_error_notification("Döngü Sırasında Olay Tespit Edildi", error_details)

            if not collected_readings:
                logger.warning("Veri toplama patlaması sonucunda hiç veri elde edilemedi.")
                self._print_summary(ProcessedReading(), status_icon="❌")
                return

            summary_reading = self.processor.analyze_burst_readings(collected_readings)
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading])
            
            summary_status_icon = "⚠️" if cycle_events else "✅"
            self._print_summary(summary_reading, status_icon=summary_status_icon)
            logger.info("Döngü başarıyla tamamlandı.")
        except Exception:
            logger.critical("Veri toplama döngüsünde kritik bir hata oluştu!", exc_info=True)
            self.notification_service.send_error_notification("Kritik Döngü Hatası", traceback.format_exc())
        finally:
            self.sensor_manager.disconnect_all()
            logger.info("Sensörler bir sonraki döngüye kadar kapatıldı.")
            self.console.print("[dim]Sensörler bir sonraki döngüye kadar kapatıldı.[/dim]")

    def _print_cycle_report(self, events: List[Dict[str, str]]):
        """Tespit edilen tüm olayları düzenli bir tablo formatında konsola basar."""
        table = Table(title=f"📋 Döngü Özet Raporu ({datetime.now().strftime('%H:%M:%S')}) 📋", style="default", title_style="bold blue")
        table.add_column("Olay Kategorisi", style="cyan", no_wrap=True)
        table.add_column("Durum", style="default")
        table.add_column("Detay", style="default")
        for event in events:
            status_style = "bold red" if "BAŞARISIZ" in event["status"] else "bold yellow"
            table.add_row(event["category"], f"[{status_style}]{event['status']}[/{status_style}]", event["detail"])
        self.console.print(table)
    
    def _print_summary(self, summary: ProcessedReading, status_icon: str):
        # ... Bu metodda değişiklik yok ...
        now=datetime.now(); next_run_time=now+timedelta(minutes=settings.DATA_COLLECTION_INTERVAL_MINUTES)
        h_str=f"{summary.snow_height_mm:.1f} mm" if summary.snow_height_mm is not None else "N/A"
        w_str=f"{summary.weight_g:.0f} g" if summary.weight_g is not None else "N/A"
        source_icon="📡" if summary.temp_hum_source=="api" else "🔌"
        t_str=f"{summary.temperature_c:.1f}°C" if summary.temperature_c is not None else "N/A"
        hu_str=f"{summary.humidity_perc:.1f}%" if summary.humidity_perc is not None else "N/A"
        summary_line=(f"[white on black][{now.strftime('%H:%M:%S')}][/white on black] {status_icon} | 📏 [bold cyan]{h_str.ljust(9)}[/bold cyan] | ⚖️  [bold green]{w_str.ljust(8)}[/bold green] | {source_icon}🌡️ [bold yellow]{t_str.ljust(7)}[/bold yellow] | 💧 [bold blue]{hu_str.ljust(6)}[/bold blue] | ⏳ [dim]{next_run_time.strftime('%H:%M')}[/dim]")
        self.console.print(summary_line)

    def run_forever(self):
        # ... Bu metodda değişiklik yok ...
        logger.info("Meteoroloji İstasyonu Servisi Başlatılıyor...")
        self.notification_service.send_startup_notification()
        self.setup_schedule()
        self.console.print("\n[bold green]✨ Sistem aktif. İlk döngü hemen başlatılıyor...[/bold green]")
        self.run_collection_cycle()
        self.console.print(f"\n[bold green]✨ Normal zamanlama döngüsü bekleniyor. Sonraki çalışma yaklaşık {settings.DATA_COLLECTION_INTERVAL_MINUTES} dakika içinde.[/bold green]")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[bold red]🛑 Program kullanıcı tarafından durduruldu.[/bold red]")
        finally:
            logger.info("👋 Hoşçakalın!")
            self.console.print("[bold blue]👋 Program sonlandırıldı.[/bold blue]")