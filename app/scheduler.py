# app/scheduler.py - GELİŞMİŞ LOGLAMA ENTEGRE EDİLMİŞ VERSİYON

import schedule
import time
import logging  # EKLENDİ
from datetime import datetime, timedelta
from tqdm import tqdm

from app.config import settings
from app.sensors.manager import SensorManager
from app.core.collector import DataCollector
from app.core.processor import DataProcessor
from app.services.database import DatabaseService
from app.services.storage import CsvStorageService
from app.services.notification import NotificationService
from app.core.logging_config import setup_logging  # EKLENDİ

logger = logging.getLogger(__name__)  # EKLENDİ

class JobScheduler:
    def __init__(self):
        self.sensor_manager = SensorManager()
        self.collector = DataCollector(self.sensor_manager)
        self.processor = DataProcessor()
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()
        self.last_summary_line = ""

    def setup_schedule(self):
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle_task)
        logger.info(f"Zamanlanmış görev ayarlandı: Her {interval} dakikada bir çalışacak.")

    def _print_summary(self, summary_reading: "ProcessedReading", status_icon: str = "✅"):
        # BU BÖLÜM BİR KULLANICI ARAYÜZÜ OLDUĞU İÇİN 'print' KULLANMAYA DEVAM EDİYOR
        now = datetime.now()
        next_run_time = now + timedelta(minutes=settings.DATA_COLLECTION_INTERVAL_MINUTES)
        
        h_str = f"{summary_reading.snow_height_mm:.1f} mm" if summary_reading.snow_height_mm is not None else "N/A"
        w_str = f"{summary_reading.weight_g:.0f} g" if summary_reading.weight_g is not None else "N/A"
        t_str = f"{summary_reading.temperature_c:.1f}°C" if summary_reading.temperature_c is not None else "N/A"
        hu_str = f"{summary_reading.humidity_perc:.1f}%" if summary_reading.humidity_perc is not None else "N/A"

        summary_line = (
            f"[{now.strftime('%H:%M:%S')}] {status_icon} | "
            f"📏 {h_str.ljust(9)} | "
            f"⚖️ {w_str.ljust(9)} | "
            f"🌡️ {t_str.ljust(7)} | "
            f"💧 {hu_str.ljust(6)} | "
            f"⏳ {next_run_time.strftime('%H:%M')}"
        )
        
        print(' ' * len(self.last_summary_line), end='\r')
        print(summary_line, end='\r')
        self.last_summary_line = summary_line

    def run_collection_cycle_task(self):
        logger.debug("Veri toplama döngüsü başlıyor...")
        collected_readings = []
        try:
            burst_duration_seconds = settings.DATA_BURST_DURATION_MINUTES * 60
            sample_interval = settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS
            
            with tqdm(total=burst_duration_seconds, desc="🔥 Veri Toplanıyor", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s", leave=False, file=sys.stdout) as pbar:
                end_time = time.time() + burst_duration_seconds
                while time.time() < end_time:
                    # ... (iç döngü aynı kalıyor)
                    start_loop_time = time.time()
                    reading = self.collector.collect_single_reading()
                    processed = self.processor.process(reading)
                    collected_readings.append(processed)
                    loop_duration = time.time() - start_loop_time
                    sleep_time = max(0, sample_interval - loop_duration)
                    time.sleep(sleep_time)
                    pbar.update(sample_interval)

            if not collected_readings:
                logger.warning("Döngüde hiç veri toplanamadı.")
                return

            summary_reading = self.processor.analyze_readings(collected_readings)
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading])

            self._print_summary(summary_reading, status_icon="✅")
            logger.info(f"Döngü tamamlandı. {len(collected_readings)} örnek işlendi.")

        except Exception as e:
            # exc_info=True, hatanın traceback'ini log dosyasına otomatik ekler.
            logger.error(f"Veri toplama döngüsünde beklenmedik hata", exc_info=True)
            error_title = "Döngü Hatası"
            error_details = f"Detaylar için log dosyasını kontrol edin: meteo_station.log"
            self.notification_service.send_error_notification(error_title, error_details)

            # Arayüzde hata bildirimi
            now_str = datetime.now().strftime('%H:%M:%S')
            error_line = f"[{now_str}] ❌ | Hata oluştu. Detaylar log dosyasında."
            print(' ' * len(self.last_summary_line), end='\r')
            print(error_line)
            self.last_summary_line = error_line

    def run(self):
        setup_logging()  # Loglama sistemini en başta kur
        logger.info("🚀 Meteoroloji İstasyonu Başlatılıyor...")
        
        self.sensor_manager.discover_ports()
        self.sensor_manager.connect()
        self.notification_service.send_startup_notification()
        self.setup_schedule()
        
        print("---")
        print(f"✨ Sistem aktif. İlk döngü çalıştırılıyor...")
        
        self.run_collection_cycle_task()

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Program kullanıcı tarafından durduruldu.")
            logger.info("Program kullanıcı tarafından durduruldu.")
        finally:
            self.sensor_manager.disconnect()
            logger.info("👋 Hoşçakalın!")