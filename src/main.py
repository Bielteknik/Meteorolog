from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from modules.sensor_manager import SensorManager
from modules.data_processor import DataProcessor
from modules.storage_manager import StorageManager
from modules.rich_display import RichDisplay

CONFIG_PATH, DB_PATH = '../config/config.yaml', '../data/database/station_data.db'

class MeteorologyStation:
    def __init__(self):
        self.display = RichDisplay()
        self.display.print_startup_banner()
        
        with open(CONFIG_PATH, 'r') as f: self.config = yaml.safe_load(f)
        
        self.system_status = {'sensors': {}, 'last_collection': {}, 'next_job': {}}
        self.sensor_manager = SensorManager(self.config)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(DB_PATH)
        self.scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        
    def setup_jobs(self):
        interval = self.config['scheduler']['data_collection_interval_minutes']
        self.scheduler.add_job(self.run_collection_cycle, 'interval', minutes=interval, id='collect_job', name="Veri Toplama")
        print(f"INFO: Veri toplama görevi her {interval} dakikada bir ayarlandı.")

    def update_dashboard(self):
        # Seri sensörler
        assigned = self.sensor_manager.get_assigned_ports()
        for name in ['distance', 'weight']:
            self.system_status['sensors'][name] = {'connected': name in assigned, 'detail': f"Port: {assigned.get(name, 'Bulunamadı')}"}
        # I2C sensörü (durumu döngüde güncellenir, başlangıçta varsayım)
        self.system_status['sensors']['temperature_humidity'] = self.system_status['sensors'].get('temperature_humidity', {'connected': False, 'detail': 'Test ediliyor...'})
        
        # Sonraki görev
        if jobs := self.scheduler.get_jobs():
            next_job = min(jobs, key=lambda j: j.next_run_time)
            self.system_status['next_job'] = {'name': next_job.name, 'time': next_job.next_run_time.strftime('%H:%M:%S')}
        self.display.print_status_dashboard(self.system_status)

    def run_collection_cycle(self):
        self.display.print_collection_header()
        raw_data = self.sensor_manager.read_all_sensors()
        
        self.system_status['last_collection']['status'] = 'Success' if raw_data else 'Failure'
        self.system_status['last_collection']['time'] = datetime.now().strftime('%H:%M:%S')
        
        i2c_name, i2c_status = 'temperature_humidity', 'temperature_c' in raw_data and raw_data['temperature_c'] is not None
        self.system_status['sensors'][i2c_name] = {'connected': i2c_status, 'detail': "Veri okundu" if i2c_status else "Okuma hatası"}
        
        processed_data = self.data_processor.process_reading_data(raw_data)
        if processed_data:
            processed_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.storage_manager.save_reading(processed_data)
        
        self.display.print_collection_result(processed_data)
        self.update_dashboard()

    def start(self):
        self.sensor_manager.find_and_assign_sensors()
        self.setup_jobs()
        self.update_dashboard()
        print("\n...CTRL+C ile çıkış yapabilirsiniz...")
        self.scheduler.start()

if __name__ == "__main__":
    try:
        station = MeteorologyStation()
        station.start()
    except Exception as e:
        print(f"\nCRITICAL: Sistem başlatılamadı! Hata: {e}")