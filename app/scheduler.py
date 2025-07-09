# app/scheduler.py - ÖZET ÇIKTILI, SESSİZ VERSİYON

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
        print("🗓️  Zamanlanmış görev ayarlanıyor...")
        
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle_task)
    
        print(f"  - Ana döngü her {interval} dakikada bir çalışacak.")
        print(f"  - İlk döngü test amaçlı olarak hemen şimdi başlatılacak.")

    def run_collection_cycle_task(self):
        """
        Bir tam veri toplama, işleme ve kaydetme döngüsünü yönetir.
        Artık döngü sırasında değil, döngü sonunda özet bilgi yazdırır.
        """
        job_name = "Veri Toplama Döngüsü"
        start_time_str = datetime.now().strftime('%H:%M:%S')
        print(f"\n--- 🚀 GÖREV BAŞLADI: {job_name} [{start_time_str}] ---")
        
        collected_readings = []
        try:
            # 1. Veri Toplama Patlaması (Data Burst)
            burst_duration = timedelta(minutes=settings.DATA_BURST_DURATION_MINUTES)
            sample_interval = settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS
            end_time = datetime.now() + burst_duration
            
            # --- YENİ: Dinamik "bekleniyor" animasyonu ---
            print(f"  🔥 Veri toplama patlaması başladı ({burst_duration.total_seconds() / 60:.1f} dakika)... ", end="", flush=True)
            
            animation = "|/-\\"
            idx = 0
            
            try:
                while datetime.now() < end_time:
                    # Anlık okumalar sessizce toplanır
                    reading = self.collector.collect_single_reading()
                    processed = self.processor.process(reading)
                    collected_readings.append(processed)
                    
                    # Kullanıcıya sistemin çalıştığını gösteren animasyon
                    print(animation[idx % len(animation)], end="\b", flush=True)
                    idx += 1
                    
                    time.sleep(sample_interval)
            except KeyboardInterrupt:
                print("\n  🛑 Veri toplama döngüsü kullanıcı tarafından yarıda kesildi.")
                pass
            
            print("✓") # Animasyonu bitirip onay işareti koy
            
            sample_count = len(collected_readings)
            print(f"  🎉 Patlama bitti. Toplam {sample_count} örnek alındı.")
    
            # 2. Analiz
            if not collected_readings:
                print("  ⚠️ Döngüde hiç veri toplanamadı. Kayıt atlanıyor.")
                return
    
            #print("  📊 Toplanan veriler analiz ediliyor (ortalama hesaplanıyor)...")
            summary_reading = self.processor.analyze_readings(collected_readings)
            
            # --- YENİ: Analiz sonucunu güzel bir formatta yazdır ---
            print("  📊 Analiz Sonucu (Ortalama Değerler):")
            h_str = f"{summary_reading.snow_height_mm:7.1f}" if summary_reading.snow_height_mm is not None else "  N/A  "
            w_str = f"{summary_reading.weight_g:7.1f}" if summary_reading.weight_g is not None else "  N/A  "
            t_str = f"{summary_reading.temperature_c:5.1f}" if summary_reading.temperature_c is not None else " N/A "
            hu_str = f"{summary_reading.humidity_perc:5.1f}" if summary_reading.humidity_perc is not None else " N/A "
            d_str = f"{summary_reading.density_kg_m3:6.1f}" if summary_reading.density_kg_m3 is not None else "  N/A "

            print(f"  └─ 📏 Kar Yük.: {h_str} mm | ⚖️ Ağırlık: {w_str} g | 🌡️ Isı: {t_str} °C | 💧 Nem: {hu_str} % | 🧱 Yoğunluk: {d_str} kg/m³")
            # ------------------------------------------------------------

            # 3. Kayıt
            print("  💾 Özet veri veritabanına ve CSV'ye kaydediliyor...")
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading])
    
            print("  ✨ Döngü başarıyla tamamlandı.")
    
        except Exception as e:
            error_title = f"{job_name} Görev Hatası"
            error_details = f"Hata: {e}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"  ❌ HATA: {error_title}\n{error_details}")
            self.notification_service.send_error_notification(error_title, error_details)
        
        finally:
            end_time_str = datetime.now().strftime('%H:%M:%S')
            print(f"--- ✅ GÖREV BİTTİ: {job_name} [{end_time_str}] ---")

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