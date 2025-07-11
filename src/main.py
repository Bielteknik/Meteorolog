import time
from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

# Modülleri içe aktar
from modules.sensor_manager import SensorManager
from modules.data_processor import DataProcessor
from modules.storage_manager import StorageManager

CONFIG_PATH = '../config/config.yaml'
DB_PATH = '../data/database/station_data.db'

class MeteorologyStation:
    def __init__(self, config_path, db_path):
        print("=============================================")
        print("=  Kar Gözlem ve Çığ Tahmin İstasyonu v0.2  =")
        print("=============================================")
        
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise SystemExit(f"CRITICAL: Yapılandırma dosyası bulunamadı: {config_path}")

        # Modülleri başlat
        self.sensor_manager = SensorManager(config_path)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(db_path)

        # Durum Makinesi için başlangıç durumu
        self.state = "INITIALIZING"
        print(f"INFO: Sistem durumu: {self.state}")

    def startup(self):
        """Sistemin başlangıç prosedürleri."""
        self.state = "SENSOR_DISCOVERY"
        print(f"\n--- DURUM: {self.state} ---")
        # Sensörleri bul ve ata
        if not self.sensor_manager.find_and_assign_sensors():
            print("WARNING: Tüm sensörler bulunamadı, sistem kısıtlı modda çalışacak.")
        
        self.state = "IDLE"
        print(f"\n--- DURUM: {self.state} ---")
        print("INFO: Başlatma prosedürü tamamlandı. Zamanlanmış görevler bekleniyor...")

    def collect_process_store_job(self):
        """Zamanlayıcı tarafından periyodik olarak çalıştırılacak ana görev."""
        print("\n" + "="*50)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Periyodik görev başlatıldı.")
        
        # 1. Veri Toplama
        self.state = "COLLECTING_DATA"
        print(f"--- DURUM: {self.state} ---")
        raw_data = self.sensor_manager.read_all_sensors()
        if not raw_data:
            print("WARNING: Hiçbir sensörden veri toplanamadı. Görev sonlandırılıyor.")
            self.state = "IDLE"
            return
        print(f"SUCCESS: Ham veriler toplandı: {raw_data}")

        # 2. Veri İşleme
        self.state = "PROCESSING_DATA"
        print(f"--- DURUM: {self.state} ---")
        processed_data = {}
        # Ham verileri parse et
        for sensor_name, value in raw_data.items():
            parsed_value = self.data_processor.parse_raw_data(sensor_name, value)
            # İsimleri daha anlamlı hale getir (distance -> distance_mm)
            if parsed_value is not None:
                if sensor_name == 'distance':
                    processed_data['distance_mm'] = parsed_value
                elif sensor_name == 'weight':
                    processed_data['weight_g'] = parsed_value
        
        # Türetilmiş değerleri hesapla (Kar Yüksekliği, Yoğunluk vb.)
        final_data = self.data_processor.calculate_derived_values(processed_data)
        final_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"SUCCESS: Veriler işlendi: {final_data}")

        # 3. Veri Saklama
        self.state = "STORING_DATA"
        print(f"--- DURUM: {self.state} ---")
        self.storage_manager.save_reading(final_data)
        
        self.state = "IDLE"
        print(f"--- DURUM: {self.state} ---")
        print("Periyodik görev başarıyla tamamlandı.")
        print("="*50 + "\n")


if __name__ == "__main__":
    station = MeteorologyStation(config_path=CONFIG_PATH, db_path=DB_PATH)
    station.startup()
    
    # Görev Zamanlayıcı
    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    # Test için her 1 dakikada bir çalıştır. Normalde 'minutes=15' olacak.
    scheduler.add_job(station.collect_process_store_job, 'interval', minutes=1, id='main_job')
    
    print(f"INFO: Ana görev '{scheduler.get_job('main_job').name}' her {1} dakikada bir çalışacak şekilde ayarlandı.")
    print("...CTRL+C ile çıkış yapabilirsiniz...")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nINFO: Program sonlandırılıyor.")