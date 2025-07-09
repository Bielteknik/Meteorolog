import schedule
import time
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import List
from tqdm import tqdm

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
        # Tüm servisleri ve yöneticileri başlat
        self.sensor_manager = SensorManager()
        self.collector = DataCollector(self.sensor_manager)
        self.processor = DataProcessor()
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()
        self.last_summary_line = ""

    def setup_schedule(self):
        """Ana veri toplama döngüsünü zamanlar."""
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle)
        logger.info(f"Ana görev {interval} dakikada bir çalışacak şekilde ayarlandı.")

    def run_collection_cycle(self):
        """Bir tam veri toplama, işleme ve kaydetme döngüsünü yönetir."""
        logger.info("Veri toplama döngüsü başlatılıyor...")
        collected_readings: List[ProcessedReading] = []
        
        try:
            burst_duration = timedelta(minutes=settings.DATA_BURST_DURATION_MINUTES)
            sample_interval = timedelta(seconds=settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS)
            end_time = datetime.now() + burst_duration

            # İlerleme çubuğu ile veri toplama (burst mode)
            with tqdm(total=int(burst_duration.total_seconds()), desc="🔥 Veri Toplanıyor", bar_format="{l_bar}{bar}|", file=sys.stdout, leave=False) as pbar:
                while datetime.now() < end_time:
                    start_loop_time = time.time()
                    
                    raw_data = self.collector.collect_raw_data()
                    processed_data = self.processor.process_raw_data(raw_data)
                    collected_readings.append(processed_data)

                    loop_duration = time.time() - start_loop_time
                    sleep_time = max(0, sample_interval.total_seconds() - loop_duration)
                    time.sleep(sleep_time)
                    pbar.update(int(sample_interval.total_seconds()))

            # Toplanan verileri analiz et
            if not collected_readings:
                logger.warning("Veri toplama patlaması sonucunda hiç veri elde edilemedi.")
                self._print_summary(ProcessedReading(), status_icon="⚠️")
                return

            summary_reading = self.processor.analyze_burst_readings(collected_readings)
            
            # Analiz edilen veriyi kaydet
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading])
            
            self._print_summary(summary_reading, status_icon="✅")
            logger.info(f"Döngü başarıyla tamamlandı. {len(collected_readings)} anlık okumanın ortalaması kaydedildi.")

        except Exception:
            logger.critical("Veri toplama döngüsünde kritik bir hata oluştu!", exc_info=True)
            self.notification_service.send_error_notification("Kritik Döngü Hatası", traceback.format_exc())
            self._print_summary(ProcessedReading(), status_icon="❌") # Hata durumunda boş özet bas

    def _print_summary(self, summary: ProcessedReading, status_icon: str):
        """
        Analiz sonucunu ve bir sonraki çalışma zamanını tek bir satırda yazdırır.
        """
        now = datetime.now()
        next_run_time = now + timedelta(minutes=settings.DATA_COLLECTION_INTERVAL_MINUTES)

        # Değerleri formatla, None ise N/A yaz
        h_str = f"{summary.snow_height_mm:.1f} mm" if summary.snow_height_mm is not None else "N/A"
        w_str = f"{summary.weight_g:.0f} g" if summary.weight_g is not None else "N/A"
        t_str = f"{summary.temperature_c:.1f}°C" if summary.temperature_c is not None else "N/A"
        hu_str = f"{summary.humidity_perc:.1f}%" if summary.humidity_perc is not None else "N/A"

        summary_line = (
            f"[{now.strftime('%H:%M:%S')}] {status_icon} | "
            f"📏 {h_str.ljust(9)} | "
            f"⚖️ {w_str.ljust(9)} | "
            f"🌡️ {t_str.ljust(7)} | "
            f"💧 {hu_str.ljust(6)} | "
            f"⏳ {next_run_time.strftime('%H:%M')}"
        )
        
        # Önceki satırı temizlemek için boşluklarla doldur ve satır başına dön
        print(' ' * len(self.last_summary_line), file=sys.stdout, end='\r')
        self.last_summary_line = summary_line
        print(self.last_summary_line, file=sys.stdout, end='\r')

    def run_forever(self):
        """Zamanlayıcıyı başlatır ve sonsuz döngüde çalıştırır."""
        logger.info("🚀 Meteoroloji İstasyonu Servisi Başlatılıyor...")
        self.sensor_manager.discover_and_connect()
        self.notification_service.send_startup_notification()
        self.setup_schedule()
        
        print("---")
        # İlk döngüyü hemen başlatmak, sistemin çalıştığını görmek için iyidir.
        print("✨ Sistem aktif. Test için ilk döngü hemen başlatılıyor...")
        self.run_collection_cycle()
        print(f"\n✨ Normal zamanlama döngüsü bekleniyor. Sonraki çalışma yaklaşık {settings.DATA_COLLECTION_INTERVAL_MINUTES} dakika içinde.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1) # CPU'yu yormamak için 1 saniye bekle
        except KeyboardInterrupt:
            print("\n🛑 Program kullanıcı tarafından durduruldu.")
            logger.info("Program kullanıcı tarafından durduruldu.")
        finally:
            self.sensor_manager.disconnect_all()
            logger.info("👋 Hoşçakalın!")