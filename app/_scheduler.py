# app/scheduler.py - NİHAİ VERSİYON

import schedule
import time
import traceback
from datetime import datetime
from typing import List

# Gerekli ayarları ve sınıfları import et
from app.config import _settings
from app.models.schemas import ProcessedReading
from app.sensors.manager import SensorManager
from app.core.collector import DataCollector
from app.core.processor import DataProcessor
from app.services.database import DatabaseService
from app.services.storage import CsvStorageService
from app.services.notification import NotificationService

class JobScheduler:
    """Tüm zamanlanmış görevleri ve servisleri yöneten ana sınıf."""
    
    def __init__(self):
        """Servisleri ve yöneticileri başlatır."""
        self.sensor_manager = SensorManager()
        self.collector = DataCollector(self.sensor_manager)
        self.processor = DataProcessor()
        self.db_service = DatabaseService()
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()

        # Okumaları geçici olarak biriktirmek için bir buffer listesi
        self.readings_buffer: List[ProcessedReading] = []

    def setup_schedule(self):
        """Tüm zamanlanmış görevleri ayarlar."""
        print("🗓️ Zamanlanmış görevler ayarlanıyor...")
        
        # Görevleri doğrudan 'do()' metoduna veriyoruz.
        # Hata yönetimi artık her görevin kendi içinde yapılacak.
        schedule.every(1).seconds.do(self.collect_and_process_data_task)
        schedule.every(_settings.DATA_COLLECTION_DURATION_SECONDS).seconds.do(self.save_buffered_data_task)
    
        print(f"  - Her saniye veri okunacak.")
        print(f"  - Her {_settings.DATA_COLLECTION_DURATION_SECONDS} saniyede bir veriler kaydedilecek.")

    def collect_and_process_data_task(self):
        """Sensörlerden veri okur, işler ve buffer'a ekler. Hata yönetimi içerir."""
        job_name = "Veri Toplama ve İşleme"
        try:
            # Ham veriyi topla
            reading = self.collector.collect_single_reading()
            
            # Veriyi işle (kar yüksekliği, yoğunluk vb. hesapla)
            processed = self.processor.process(reading)
            
            # İşlenmiş veriyi buffer'a ekle
            self.readings_buffer.append(processed)
            
            # None (boş) değerleri için daha güvenli bir yazdırma formatı
            h = f"{processed.height_mm:.2f}" if processed.height_mm is not None else "N/A"
            w = f"{processed.weight_g:.2f}" if processed.weight_g is not None else "N/A"
            t = f"{processed.temperature_c:.2f}" if processed.temperature_c is not None else "N/A"
            hu = f"{processed.humidity_perc:.2f}" if processed.humidity_perc is not None else "N/A"

            # Konsola anlık durumu yazdır
            print(f"-> Okuma: Yükseklik={h}mm, Ağırlık={w}g, Sıcaklık={t}°C, Nem={hu}%")

        except Exception as e:
            # Hata durumunda logla ve bildirim gönder
            error_title = f"{job_name} Görev Hatası"
            error_details = f"Hata: {e}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"❌ {error_title}\n{error_details}")
            self.notification_service.send_error_notification(error_title, error_details)

    def save_buffered_data_task(self):
        """Buffer'da biriken verileri veritabanına ve CSV'ye kaydeder. Hata yönetimi içerir."""
        job_name = "Toplu Veri Kaydetme"
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Görev Başladı: {job_name} ---")
        try:
            if not self.readings_buffer:
                print("ℹ️ Kaydedilecek yeni veri bulunmuyor.")
                return

            # Verileri topluca kaydet
            self.db_service.save_bulk_readings(self.readings_buffer)
            self.csv_service.save_readings_to_csv(self.readings_buffer)

            print(f"✅ {len(self.readings_buffer)} adet okuma kaydedildi. Buffer temizleniyor.")
            # Buffer'ı temizle
            self.readings_buffer.clear()
        
        except Exception as e:
            # Hata durumunda logla ve bildirim gönder
            error_title = f"{job_name} Görev Hatası"
            error_details = f"Hata: {e}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"❌ {error_title}\n{error_details}")
            self.notification_service.send_error_notification(error_title, error_details)
        
        finally:
            # Görevin bittiğini belirt
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Görev Bitti: {job_name} ---")

    def run(self):
        """Zamanlayıcıyı başlatır ve sonsuz döngüde çalıştırır."""
        print("🚀 Meteoroloji İstasyonu Başlatılıyor...")
        
        # Başlangıçta portları bul ve bağlan
        self.sensor_manager.discover_ports()
        self.sensor_manager.connect()
        
        # Başlangıç bildirimi gönder
        self.notification_service.send_startup_notification()

        # Zamanlanmış görevleri kur
        self.setup_schedule()
        
        print("\n✨ Veri toplama döngüsü başlıyor...")
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