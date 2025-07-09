import schedule
import time
import traceback
from datetime import datetime
from typing import List

from app.config import settings
from app.models.schemas import ProcessedReading
from app.sensors.manager import SensorManager
from app.core.collector import DataCollector
from app.core.processor import DataProcessor
from app.services.database import DatabaseService
from app.services.storage import CsvStorageService
from app.services.notification import NotificationService

class JobScheduler:
    def __init__(self):
        # Servisleri ve yöneticileri başlat
        self.sensor_manager = SensorManager()
        self.collector = DataCollector(self.sensor_manager)
        self.processor = DataProcessor()
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()

        # Veri toplama döngüsü için geçici bir liste
        self.readings_buffer: List[ProcessedReading] = []

    def _run_safely(self, job_func, job_name: str):
        """Bir görevi güvenli bir şekilde çalıştırır ve hata durumunda bildirim gönderir."""
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Görev Başladı: {job_name} ---")
            job_func()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Görev Bitti: {job_name} ---")
        except Exception as e:
            error_title = f"{job_name} Görev Hatası"
            error_details = f"Hata: {e}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"❌ {error_title}\n{error_details}")
            self.notification_service.send_error_notification(error_title, error_details)

    def setup_schedule(self):
        """Tüm zamanlanmış görevleri ayarlar."""
        print("🗓️ Zamanlanmış görevler ayarlanıyor...")
        
        # 'do' metoduna fonksiyonu ilk argüman olarak,
        # diğer parametreleri ise anahtar kelime argümanları (kwargs) olarak iletiyoruz.
        # Bu, 'TypeError' hatasını çözer.
        
        schedule.every(1).seconds.do(
            self._run_safely,
            job_func=self.collect_and_process_data_task,
            job_name="Veri Toplama ve İşleme"
        )
    
        schedule.every(settings.DATA_COLLECTION_DURATION_SECONDS).seconds.do(
            self._run_safely,
            job_func=self.save_buffered_data_task,
            job_name="Toplu Veri Kaydetme"
        )
    
        print(f"  - Her saniye veri okunacak.")
        print(f"  - Her {settings.DATA_COLLECTION_DURATION_SECONDS} saniyede bir veriler kaydedilecek.")

    def collect_and_process_data_task(self):
        """Sensörlerden veri okur, işler ve buffer'a ekler."""
        # Ham veriyi topla
        reading = self.collector.collect_single_reading()
        
        # Veriyi işle (kar yüksekliği, yoğunluk vb. hesapla)
        processed = self.processor.process(reading)
        
        # İşlenmiş veriyi buffer'a ekle
        self.readings_buffer.append(processed)
        
        # Konsola anlık durumu yazdır (isteğe bağlı)
        print(f"-> Okuma: Yükseklik={processed.height_mm}mm, Ağırlık={processed.weight_g}g, Sıcaklık={processed.temperature_c}°C, Nem={processed.humidity_perc}%")

    def save_buffered_data_task(self):
        """Buffer'da biriken verileri veritabanına ve CSV'ye kaydeder."""
        if not self.readings_buffer:
            print("ℹ️ Kaydedilecek yeni veri bulunmuyor.")
            return

        # Verileri topluca kaydet
        self.db_service.save_bulk_readings(self.readings_buffer)
        self.csv_service.save_readings_to_csv(self.readings_buffer)

        # Buffer'ı temizle
        print(f"✅ {len(self.readings_buffer)} adet okuma kaydedildi. Buffer temizleniyor.")
        self.readings_buffer.clear()

    def run(self):
        """Zamanlayıcıyı başlatır ve sonsuz döngüde çalıştırır."""
        # Başlangıçta portları bul ve bağlan
        self.sensor_manager.discover_ports()
        self.sensor_manager.connect()
        
        # Başlangıç bildirimi gönder
        self.notification_service.send_startup_notification()

        # Zamanlanmış görevleri kur
        self.setup_schedule()
        
        print("\n🚀 Meteoroloji İstasyonu Başlatıldı! Veri toplama döngüsü başlıyor...")
        try:
            while True:
                schedule.run_pending()
                time.sleep(0.1) # CPU kullanımını düşürmek için kısa bir bekleme
        except KeyboardInterrupt:
            print("\n🛑 Program kullanıcı tarafından durduruldu.")
        finally:
            # Kapanışta tüm bağlantıları güvenli bir şekilde kapat
            self.sensor_manager.disconnect()
            print("👋 Hoşçakalın!")