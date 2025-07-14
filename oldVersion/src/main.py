from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

# Modülleri içe aktar
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
        with open(CONFIG_PATH, 'r') as f: self.config = yaml.safe_load(f)
        
        self.system_status = {'sensors': {}, 'last_collection': {}, 'next_job': {}}
        
        self.modules = {
            'sensor': SensorManager(self.config),
            'processor': DataProcessor(self.config),
            'storage': StorageManager(DB_PATH),
            'weather': WeatherApiManager(self.config)
        }
        self.scheduler = BlockingScheduler(timezone="Europe/Istanbul")

    def setup_jobs(self):
        self.interval = self.config['scheduler']['data_collection_interval_minutes']
        self.scheduler.add_job(self.run_collection_cycle, 'interval', minutes=self.interval, id='collect_job')
        if self.modules['weather'].api_key:
            api_interval = self.config['openweathermap']['cache_update_interval_hours']
            self.scheduler.add_job(self.modules['weather'].get_weather_data, 'interval', hours=api_interval)
        print(f"INFO: Görevler ayarlandı. Veri toplama: {self.interval} dk.")

    def update_dashboard(self):
        assigned = self.modules['sensor'].get_assigned_ports()
        for name in ['distance', 'weight', 'temperature_humidity']:
            status = self.system_status['sensors'].get(name, {})
            if 'identifier_pattern' in self.config['sensors'][name]: # Seri sensörler için
                status['connected'] = name in assigned
                status['detail'] = f"Port: {assigned.get(name, 'Bulunamadı')}"
            self.system_status['sensors'][name] = status
        self.system_status['next_job']['time'] = f"Her {self.interval} dk'da bir"
        self.display.print_status_dashboard(self.system_status)

    def run_collection_cycle(self):
        self.display.print_collection_header()
        raw = self.modules['sensor'].read_all_sensors()
        
        # Yedekleme mantığı
        i2c_name = 'temperature_humidity'
        i2c_ok = 'temperature_c' in raw and raw['temperature_c'] is not None
        if not i2c_ok and (cached := self.modules['weather'].get_cached_data()):
            print("WARNING: I2C okunamadı. Yedek (API) kullanılıyor.")
            raw.update(cached)
            self.system_status['sensors'][i2c_name] = {'connected': False, 'detail': "YEDEK MOD: API"}
        else:
            self.system_status['sensors'][i2c_name] = {'connected': i2c_ok, 'detail': "Okundu (I2C)" if i2c_ok else "Okuma hatası"}
        
        processed = self.modules['processor'].process_reading_data(raw)
        if processed:
            processed['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.modules['storage'].save_reading(processed)
        
        self.system_status['last_collection'] = {'status': 'Success' if processed else 'Failure', 'time': datetime.now().strftime('%H:%M:%S')}
        self.display.print_collection_result(processed)
        self.update_dashboard()

    def shutdown(self):
        self.display.console.print("\n[bold yellow]Kapanış prosedürü başlatılıyor...[/bold yellow]")
        if self.scheduler.running: self.scheduler.shutdown(wait=False); print("INFO: Zamanlayıcı durduruldu.")
        for module in self.modules.values():
            if hasattr(module, 'shutdown'): module.shutdown()
        self.display.console.print("[bold green]Sistem güvenli bir şekilde kapatıldı. Hoşça kalın![/bold green]")

    def start(self):
        if self.modules['weather'].api_key: self.modules['weather'].get_weather_data()
        self.modules['sensor'].find_and_assign_sensors()
        self.setup_jobs()
        print("\n✨ Sistem aktif. İlk döngü hemen başlatılıyor...")
        self.run_collection_cycle()
        print("\n...CTRL+C ile çıkış yapabilirsiniz...")
        self.scheduler.start()

if __name__ == "__main__":
    station = None
    try:
        station = MeteorologyStation()
        station.start()
    except (KeyboardInterrupt, SystemExit):
        if station: station.shutdown()
    except Exception as e:
        import traceback
        print(f"\nCRITICAL: Sistem başlatılırken ölümcül hata! Hata: {e}")
        traceback.print_exc()
        if station: station.shutdown()