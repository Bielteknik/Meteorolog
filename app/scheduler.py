# app/scheduler.py
import schedule
import time
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import List
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

logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self):
        self.console = Console()
        self.sensor_manager = SensorManager()
        self.collector = DataCollector(self.sensor_manager)
        self.processor = DataProcessor()
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()
        # DEĞİŞİKLİK: Artık bu değişkene ihtiyacımız kalmadı.
        # self.last_summary_line = ""

    def setup_schedule(self):
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle)
        logger.info(f"Ana görev {interval} dakikada bir çalışacak şekilde ayarlandı.")

    def run_collection_cycle(self):
        logger.info("Veri toplama döngüsü başlatılıyor...")
        collected_readings: List[ProcessedReading] = []
        try:
            burst_duration = timedelta(minutes=settings.DATA_BURST_DURATION_MINUTES)
            sample_interval = timedelta(seconds=settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS)
            end_time = datetime.now() + burst_duration

            # leave=True, ilerleme çubuğunun döngü bittiğinde ekranda kalmasını sağlar.
            with tqdm(total=int(burst_duration.total_seconds()), desc="[bold magenta]🔥 Veri Toplanıyor[/bold magenta]", bar_format="{l_bar}{bar}|", file=sys.stdout, leave=True) as pbar:
                while datetime.now() < end_time:
                    start_loop_time = time.time()
                    raw_data = self.collector.collect_raw_data()
                    processed_data = self.processor.process_raw_data(raw_data)
                    collected_readings.append(processed_data)
                    loop_duration = time.time() - start_loop_time
                    sleep_time = max(0, sample_interval.total_seconds() - loop_duration)
                    time.sleep(sleep_time)
                    pbar.update(int(sample_interval.total_seconds()))

            # tqdm satırından sonra yeni bir satıra geçmek için boş bir print.
            print() 

            if not collected_readings:
                logger.warning("Veri toplama patlaması sonucunda hiç veri elde edilemedi.")
                self._print_summary(ProcessedReading(), status_icon="⚠️")
                return

            summary_reading = self.processor.analyze_burst_readings(collected_readings)
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading])
            
            self._print_summary(summary_reading, status_icon="✅")
            logger.info(f"Döngü başarıyla tamamlandı. {len(collected_readings)} anlık okumanın ortalaması kaydedildi.")

        except Exception:
            logger.critical("Veri toplama döngüsünde kritik bir hata oluştu!", exc_info=True)
            self.notification_service.send_error_notification("Kritik Döngü Hatası", traceback.format_exc())
            print()
            self._print_summary(ProcessedReading(), status_icon="❌")

    def _print_summary(self, summary: ProcessedReading, status_icon: str):
        # DEĞİŞİKLİK: Çıktıyı yazdırmak için artık rich.console kullanıyoruz.
        now = datetime.now()
        next_run_time = now + timedelta(minutes=settings.DATA_COLLECTION_INTERVAL_MINUTES)
        h_str = f"{summary.snow_height_mm:.1f} mm" if summary.snow_height_mm is not None else "N/A"
        w_str = f"{summary.weight_g:.0f} g" if summary.weight_g is not None else "N/A"
        source_icon = "📡" if summary.temp_hum_source == "api" else "🔌"
        t_str = f"{summary.temperature_c:.1f}°C" if summary.temperature_c is not None else "N/A"
        hu_str = f"{summary.humidity_perc:.1f}%" if summary.humidity_perc is not None else "N/A"
        
        # rich'in biçimlendirme etiketlerini kullanarak satırı oluştur
        summary_line = (
            f"[white on black][{now.strftime('%H:%M:%S')}][/white on black] {status_icon} | "
            f"📏 [bold cyan]{h_str.ljust(9)}[/bold cyan] | "
            f"⚖️  [bold green]{w_str.ljust(8)}[/bold green] | "
            f"{source_icon}🌡️ [bold yellow]{t_str.ljust(7)}[/bold yellow] | "
            f"💧 [bold blue]{hu_str.ljust(6)}[/bold blue] | "
            f"⏳ [dim]{next_run_time.strftime('%H:%M')}[/dim]"
        )
        
        # self.console.print ile satırı yazdır. Bu, \r'den daha güvenilirdir.
        self.console.print(summary_line)

    def _print_startup_summary(self):
        # Bu fonksiyonda değişiklik yok.
        table = Table(title="🚀 Meteoroloji İstasyonu Servis Durumu 🚀", style="cyan", title_style="bold magenta")
        table.add_column("Bileşen", style="bold green"); table.add_column("Durum", style="bold"); table.add_column("Detay", style="cyan")
        h_status = "[bold green]BAŞARILI[/bold green]" if self.sensor_manager.is_height_connected else "[bold yellow]BAŞARISIZ[/bold yellow]"
        h_detail = self.sensor_manager.height_port or "Port bulunamadı."
        table.add_row("📏 Yükseklik Sensörü", h_status, h_detail)
        w_status = "[bold green]BAŞARILI[/bold green]" if self.sensor_manager.is_weight_connected else "[bold yellow]BAŞARISIZ[/bold yellow]"
        w_detail = self.sensor_manager.weight_port or "Port bulunamadı."
        table.add_row("⚖️  Ağırlık Sensörü", w_status, w_detail)
        if self.sensor_manager.is_temp_hum_connected:
            t_status = "[bold green]BAŞARILI[/bold green]"; t_detail = f"I2C Bus {settings.I2C_BUS} üzerinde bağlandı."
        else:
            t_status = "[bold red]YEDEK MOD AKTİF[/bold red]"; t_detail = f"I2C sensörü bulunamadı. OpenWeatherMap kullanılıyor."
        table.add_row("🔌/📡 Sıcaklık/Nem", t_status, t_detail)
        self.console.print(table)

    def run_forever(self):
        # Bu fonksiyonda da çıktı yönetimi dışında değişiklik yok.
        logger.info("Meteoroloji İstasyonu Servisi Başlatılıyor...")
        self.sensor_manager.discover_and_connect()
        if not self.sensor_manager.is_temp_hum_connected:
            logger.warning("I2C sensor not found on startup. Activating OWM fallback immediately.")
            self.collector.owm_service.is_fallback_active = True
            self.collector.owm_service.update_cache(force_update=True)
        self._print_startup_summary()
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
            logger.info("Program kullanıcı tarafından durduruldu.")
        finally:
            self.sensor_manager.disconnect_all()
            logger.info("👋 Hoşçakalın!")
            self.console.print("[bold blue]👋 Tüm bağlantılar kapatıldı. Hoşçakalın![/bold blue]")