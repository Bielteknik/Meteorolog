# Dosya: Meteorolog/src/main.py (Yedeklilik Mantığı ile)
from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

from modules.sensor_manager import SensorManager
from modules.data_processor import DataProcessor
from modules.storage_manager import StorageManager
from modules.rich_display import RichDisplay
from modules.weather_api_manager import WeatherApiManager # YENİ

CONFIG_PATH, DB_PATH = '../config/config.yaml', '../data/database/station_data.db'

class MeteorologyStation:
    def __init__(self):
        self.display = RichDisplay()
        self.display.print_startup_banner()
        
        with open(CONFIG_PATH, 'r') as f: self.config = yaml.safe_load(f)
        
        self.system_status = {'sensors': {}, 'last_collection': {}, 'next_job': {}}
        
        # Modülleri başlat
        self.sensor_manager = SensorManager(self.config)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(DB_PATH)
        self.weather_api = WeatherApiManager(self.config) # YENİ
        
        self.scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        
    def setup_jobs(self):
        # Veri Toplama Görevi
        collect_interval = self.config['scheduler']['data_collection_interval_minutes']
        self.scheduler.add_job(self.run_collection_cycle, 'interval', minutes=collect_interval, id='collect_job', name="Veri Toplama")
        print(f"INFO: Veri toplama görevi her {collect_interval} dakikada bir ayarlandı.")

        # API Önbellek Güncelleme Görevi (YENİ)
        if self.weather_api.api_key:
            api_interval = self.config['openweathermap']['cache_update_interval_hours']
            self.scheduler.add_job(self.weather_api.get_weather_data, 'interval', hours=api_interval, id='weather_api_job', name="Hava Durumu API Güncelleme")
            print(f"INFO: Hava durumu API önbelleği her {api_interval} saatte bir güncellenecek.")

    def startup(self):
        # Başlangıçta API'den ilk veriyi al
        if self.weather_api.api_key:
            print("\nINFO: Başlangıç için ilk hava durumu verisi alınıyor...")
            self.weather_api.get_weather_data()

        self.sensor_manager.find_and_assign_sensors()
        self.setup_jobs()
        self.update_dashboard()

    def update_dashboard(self):
        # ... (Dashboard'u oluşturan kod önceki adımdaki ile aynı) ...
        # (Sadece 'next_job' mantığını biraz daha geliştirebiliriz)
        pass # Kısalık için önceki kodun aynısı varsayılıyor

    def run_collection_cycle(self):
        self.display.print_collection_header()
        raw_data = self.sensor_manager.read_all_sensors()

        # YEDEKLİLİK MANTIĞI BURADA DEVREYE GİRİYOR
        i2c_name = 'temperature_humidity'
        i2c_okundu = 'temperature_c' in raw_data and raw_data['temperature_c'] is not None
        
        if not i2c_okundu:
            print("WARNING: I2C sensörü okunamadı. Yedek kaynak (OpenWeatherMap) deneniyor.")
            yedek_veri = self.weather_api.get_cached_data()
            if yedek_veri:
                print("INFO: Yedek API verisi başarıyla kullanıldı.")
                raw_data.update(yedek_veri)
                self.system_status['sensors'][i2c_name] = {'connected': False, 'detail': f"YEDEK MOD: API (önbellek)"}
            else:
                print("ERROR: I2C sensörü ve yedek API verisi yok!")
                self.system_status['sensors'][i2c_name] = {'connected': False, 'detail': "Okuma hatası, yedek yok"}
        else:
            self.system_status['sensors'][i2c_name] = {'connected': True, 'detail': "Veri okundu (I2C)"}
            
        # ... (Döngünün geri kalanı aynı) ...
        processed_data = self.data_processor.process_reading_data(raw_data)
        # ...
        self.update_dashboard()

    def start(self):
        self.startup()
        print("\n...CTRL+C ile çıkış yapabilirsiniz...")
        # Başlangıçta bir kere çalıştır
        self.run_collection_cycle()
        self.scheduler.start()

if __name__ == "__main__":
    try:
        station = MeteorologyStation()
        station.start()
    except Exception as e:
        import traceback
        print(f"\nCRITICAL: Sistem başlatılamadı! Hata: {e}")
        traceback.print_exc()