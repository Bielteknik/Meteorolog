import time
from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

# Modüller
from modules.sensor_manager import SensorManager
from modules.data_processor import DataProcessor
from modules.storage_manager import StorageManager
from modules.rich_display import RichDisplay
from modules.weather_api_manager import WeatherApiManager

CONFIG_PATH, DB_PATH = '../config/config.yaml', '../data/database/station_data.db'

class MeteorologyStation:
    def __init__(self):
        self.display = RichDisplay()
        self.display.print_startup_banner()
        
        try:
            with open(CONFIG_PATH, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise SystemExit(f"CRITICAL: Yapılandırma dosyası bulunamadı: {CONFIG_PATH}")

        self.system_status = {'sensors': {}, 'last_collection': {}, 'next_job': {}}
        
        # Modülleri başlat
        self.sensor_manager = SensorManager(self.config)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(DB_PATH)
        self.weather_api = WeatherApiManager(self.config)
        self.scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        print("INFO: Tüm modüller ve zamanlayıcı başarıyla başlatıldı.")
        
    def setup_jobs(self):
        interval = self.config['scheduler']['data_collection_interval_minutes']
        self.scheduler.add_job(self.run_collection_cycle, 'interval', minutes=interval, id='collect_job', name="Veri Toplama")
        if self.weather_api.api_key:
            api_interval = self.config['openweathermap']['cache_update_interval_hours']
            self.scheduler.add_job(self.weather_api.get_weather_data, 'interval', hours=api_interval, id='weather_api_job', name="Hava Durumu API Güncelleme")
        print(f"INFO: Görevler ayarlandı. Veri toplama: {interval} dk, API güncelleme: {self.config.get('openweathermap', {}).get('cache_update_interval_hours', 'N/A')} saat.")

    def update_dashboard(self):
        # ... (Bu fonksiyon önceki adımdaki ile aynı, değişiklik yok) ...
        pass # Kısalık için önceki kodun aynısı varsayılıyor

    def run_collection_cycle(self):
        # ... (Bu fonksiyon da önceki adımdaki ile aynı) ...
        pass

    def shutdown(self):
        """Sistemi güvenli bir şekilde kapatır."""
        self.display.console.print("\n[bold yellow]Kapanış prosedürü başlatıldı...[/bold yellow]")
        
        # 1. Zamanlayıcıyı kapat
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False) # Görevlerin bitmesini bekleme
            print("INFO: Zamanlayıcı durduruldu.")
            
        # 2. Sensör bağlantılarını kapat (varsa)
        # SensorManager'a bir shutdown metodu eklemek daha temiz olur.
        if hasattr(self.sensor_manager, 'shutdown'):
            self.sensor_manager.shutdown()
        
        # 3. Veritabanı bağlantısını kapat
        if hasattr(self.storage_manager, 'shutdown'):
            self.storage_manager.shutdown()
            
        self.display.console.print("[bold green]Sistem güvenli bir şekilde kapatıldı. Hoşça kalın![/bold green]")

    def start(self):
        """Sistemi başlatır ve ana döngüyü çalıştırır."""
        if self.weather_api.api_key:
            print("\nINFO: Başlangıç için ilk hava durumu verisi alınıyor...")
            self.weather_api.get_weather_data()
            
        self.sensor_manager.find_and_assign_sensors()
        self.setup_jobs()
        self.update_dashboard()
        
        print("\n...CTRL+C ile çıkış yapabilirsiniz...")
        self.run_collection_cycle()
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            # CTRL+C yakalandığında shutdown prosedürünü çağır
            self.shutdown()

if __name__ == "__main__":
    station = None
    try:
        station = MeteorologyStation()
        station.start()
    except Exception as e:
        import traceback
        print(f"\nCRITICAL: Sistem başlatılamadı! Hata: {e}")
        traceback.print_exc()
        if station:
            station.shutdown() # Başlatma sırasında hata olursa yine de kapatmayı dene