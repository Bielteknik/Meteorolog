import time
from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

# Modüller
from modules.sensor_manager import SensorManager
from modules.data_processor import DataProcessor
from modules.storage_manager import StorageManager
from modules.rich_display import RichDisplay

CONFIG_PATH = '../config/config.yaml'
DB_PATH = '../data/database/station_data.db'

class MeteorologyStation:
    def __init__(self, config_path, db_path):
        self.display = RichDisplay()
        self.display.print_startup_banner()
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise SystemExit(f"CRITICAL: Yapılandırma dosyası bulunamadı: {config_path}")

        self.system_status = {'sensors': {}, 'last_collection': {}, 'next_job': {}}
        
        self.sensor_manager = SensorManager(self.config)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(db_path)
        self.scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        print("INFO: Görev zamanlayıcı (APScheduler) başlatıldı.")
        
    def setup_jobs(self):
        collect_interval = self.config.get('scheduler', {}).get('data_collection_interval_minutes', 1)
        self.scheduler.add_job(self.run_collection_cycle, 'interval', minutes=collect_interval, id='collect_job', name="Veri Toplama")
        print(f"INFO: Veri toplama görevi her {collect_interval} dakikada bir çalışacak şekilde ayarlandı.")

    def startup(self):
        print("INFO: Sensörler keşfediliyor...")
        self.sensor_manager.find_and_assign_sensors()
        self.setup_jobs()
        self._update_status_dashboard()

    def _update_status_dashboard(self):
        assigned_ports = self.sensor_manager.get_assigned_ports()
        for name, definition in self.config.get('sensors', {}).items():
            if 'identifier_pattern' in definition or 'i2c_address' in definition:
                is_connected = name in assigned_ports if 'identifier_pattern' in definition else self.system_status.get('sensors', {}).get(name, {}).get('connected', False)
                detail = f"Port: {assigned_ports.get(name, 'Bulunamadı')}" if 'identifier_pattern' in definition else self.system_status.get('sensors', {}).get(name, {}).get('detail', 'N/A')
                self.system_status['sensors'][name] = {'connected': is_connected, 'detail': detail}
        
        jobs = self.scheduler.get_jobs()
        if jobs:
            # --- DÜZELTME: Kütüphane versiyonundan bağımsız, daha sağlam bir yöntem ---
            # 'next_run_time' özelliği APScheduler'ın 4.x versiyonu ile geldi.
            # 3.x versiyonlarında bu özellik yok. Aşağıdaki kod her iki durumda da çalışır.
            next_job = min(jobs, key=lambda j: getattr(j, 'next_run_time', datetime.max))
            next_run_time_val = getattr(next_job, 'next_run_time', None)
            
            if next_run_time_val:
                next_run_time_str = next_run_time_val.strftime('%H:%M:%S')
                self.system_status['next_job'] = {'name': next_job.name, 'time': next_run_time_str}

        self.display.print_status_dashboard(self.system_status)

    def run_collection_cycle(self):
        self.display.print_collection_header()
        raw_data = self.sensor_manager.read_all_sensors()
        
        self.system_status['last_collection'] = {
            'status': 'Success' if raw_data else 'Failure',
            'time': datetime.now().strftime('%H:%M:%S')
        }
        
        # I2C sensör durumunu anlık olarak güncelle
        i2c_name = 'temperature_humidity'
        i2c_connected = 'temperature_c' in raw_data and raw_data['temperature_c'] is not None
        self.system_status['sensors'][i2c_name] = {
            'connected': i2c_connected,
            'detail': "Veri okundu" if i2c_connected else "Bağlantı hatası veya okunamadı"
        }
        
        processed_data = self.data_processor.process_reading_data(raw_data)
        
        if processed_data:
            processed_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.storage_manager.save_reading(processed_data)
        
        self.display.print_collection_result(processed_data)
        self._update_status_dashboard()

    def start(self):
        self.startup()
        print("\n...CTRL+C ile çıkış yapabilirsiniz...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\nINFO: Program sonlandırılıyor.")

if __name__ == "__main__":
    station = MeteorologyStation(config_path=CONFIG_PATH, db_path=DB_PATH)
    station.start()