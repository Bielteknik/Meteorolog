# app/scheduler.py - "BURST MODE" İÇİN NİHAİ VERSİYON

import schedule
import time
import traceback
from datetime import datetime, timedelta

from app.config import settings
from app.sensors.manager import SensorManager
from app.core.collector import DataCollector
from app.core.processor import DataProcessor
from app.services.database import DatabaseService
from app.services.storage import CsvStorageService
from app.services.notification import NotificationService

class JobScheduler:
    def __init__(self):
        self.sensor_manager = SensorManager()
        self.collector = DataCollector(self.sensor_manager)
        self.processor = DataProcessor()
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()

    def setup_schedule(self):
        """Ana veri toplama döngüsünü zamanlar."""
        print("🗓️ Zamanlanmış görev ayarlanıyor...")
        
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle_task)
    
        print(f"  - Ana döngü her {interval} dakikada bir çalışacak.")
        print(f"  - İlk döngü test amaçlı olarak hemen şimdi başlatılacak.")

    def run_collection_cycle_task(self):
        """
        Bir tam veri toplama, işleme ve kaydetme döngüsünü yönetir.
        """
        job_name = "Veri Toplama Döngüsü"
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- GÖREV BAŞLADI: {job_name} ---")
        
        try:
            # 1. Veri Toplama Patlaması (Data Burst)
            burst_duration = timedelta(minutes=settings.DATA_BURST_DURATION_MINUTES)
            sample_interval = settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS
            end_time = datetime.now() + burst_duration
            
            print(f"🔥 Veri toplama patlaması başladı ({burst_duration.total_seconds() / 60:.1f} dakika sürecek)...")
            
            collected_readings = []
            while datetime.now() < end_time:
                reading = self.collector.collect_single_reading()
                processed = self.processor.process(reading)
                collected_readings.append(processed)
                
                h = f"{processed.height_mm:.2f}" if processed.height_mm is not None else "N/A"
                w = f"{processed.weight_g:.2f}" if processed.weight_g is not None else "N/A"
                t = f"{processed.temperature_c:.2f}" if processed.temperature_c is not None else "N/A"
                
                print(f"  -> Anlık Okuma: Yükseklik={h}mm, Ağırlık={w}g, Sıcaklık={t}°C")
                
                time.sleep(sample_interval)
            
            print(f"🔥 Veri toplama patlaması bitti. Toplam {len(collected_readings)} örnek alındı.")

            # 2. Analiz
            if not collected_readings:
                print("⚠️ Döngüde hiç veri toplanamadı. Kayıt atlanıyor.")
                return

            print("📊 Toplanan veriler analiz ediliyor (ortalama hesaplanıyor)...")
            summary_reading = self.processor.analyze_readings(collected_readings)

            # 3. Kayıt
            print("💾 Analiz sonucu veritabanına ve CSV'ye kaydediliyor...")
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading]) # CSV servisi liste beklediği için

            print("✅ Döngü başarıyla tamamlandı.")

        except Exception as e:
            error_title = f"{job_name} Görev Hatası"
            error_details = f"Hata: {e}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"❌ {error_title}\n{error_details}")
            self.notification_service.send_error_notification(error_title, error_details)
        
        finally:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- GÖREV BİTTİ: {job_name} ---")

    def run(self):
        """Zamanlayıcıyı başlatır ve sonsuz döngüde çalıştırır."""
        print("🚀 Meteoroloji İstasyonu Başlatılıyor...")
        self.sensor_manager.discover_ports()
        self.sensor_manager.connect()
        self.notification_service.send_startup_notification()
        self.setup_schedule()
        
        # İlk döngüyü hemen çalıştırarak sistemin çalıştığını teyit edelim
        self.run_collection_cycle_task()

        print(f"\n✨ Normal zamanlama döngüsü bekleniyor. Sonraki çalışma yaklaşık {settings.DATA_COLLECTION_INTERVAL_MINUTES} dakika içinde.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1) # CPU'yu yormamak için 1 saniye bekle
        except KeyboardInterrupt:
            print("\n🛑 Program kullanıcı tarafından durduruldu.")
        finally:
            self.sensor_manager.disconnect()
            print("👋 Hoşçakalın!")