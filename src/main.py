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

        # Sistem durumu sözlüğü
        self.system_status = {
            'sensors': {},
            'last_collection': {},
            'next_job': {}
        }
        
        # Modülleri başlat
        self.sensor_manager = SensorManager(self.config)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(db_path)
        
        # --- DÜZELTME: Scheduler'ı sınıfın bir parçası yap ---
        self.scheduler = BlockingScheduler(timezone="Europe/Istanbul")
        print("INFO: Görev zamanlayıcı (APScheduler) başlatıldı.")
        
    def setup_jobs(self):
        """Zamanlanmış görevleri ayarlar."""
        collect_interval = self.config.get('scheduler', {}).get('data_collection_interval_minutes', 1)
        self.scheduler.add_job(self.run_collection_cycle, 'interval', minutes=collect_interval, id='collect_job', name="Veri Toplama")
        print(f"INFO: Veri toplama görevi her {collect_interval} dakikada bir çalışacak şekilde ayarlandı.")

    def startup(self):
        """Sistemin başlangıç prosedürleri ve ilk durum kontrolü."""
        print("INFO: Sensörler keşfediliyor...")
        self.sensor_manager.find_and_assign_sensors()
        self.setup_jobs() # Görevleri kur ki bir sonraki adımı bilelim
        self._update_status_dashboard() # Artık scheduler tanımlı

    def _update_status_dashboard(self):
        """Sistem durumu sözlüğünü günceller ve paneli yazdırır."""
        assigned_ports = self.sensor_manager.get_assigned_ports()
        for name, definition in self.config.get('sensors', {}).items():
            if 'identifier_pattern' in definition:
                self.system_status['sensors'][name] = {
                    'connected': name in assigned_ports,
                    'detail': f"Port: {assigned_ports.get(name, 'Bulunamadı')}"
                }
        
        # --- DÜZELTME: scheduler yerine self.scheduler kullan ---
        jobs = self.scheduler.get_jobs()
        if jobs:
            # En yakın çalışacak görevi bul
            next_job = min(jobs, key=lambda j: j.next_run_time)
            next_run_time_str = next_job.next_run_time.strftime('%H:%M:%S')
            self.system_status['next_job'] = {'name': next_job.name, 'time': next_run_time_str}

        self.display.print_status_dashboard(self.system_status)

    def run_collection_cycle(self):
        """Zamanlayıcı tarafından periyodik olarak çalıştırılacak ana görev."""
        self.display.print_collection_header()
        raw_data = self.sensor_manager.read_all_sensors()
        self.system_status['last_collection'] = {
            'status': 'Success' if raw_data else 'Failure',
            'time': datetime.now().strftime('%H:%M:%S')
        }
        
        # --- BU KISIMDA HENÜZ İŞLEMEDİĞİMİZ VERİLER İÇİN BİR İYİLEŞTİRME ---
        # Önceki kodlarda `process_reading_data` olmadığı için ekliyorum
        processed_data = self.data_processor.process_reading_data(raw_data) if hasattr(self.data_processor, 'process_reading_data') else raw_data

        if processed_data:
            processed_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.storage_manager.save_reading(processed_data)
        
        self.display.print_collection_result(processed_data)
        self._update_status_dashboard()

    def start(self):
        """Sistemi başlatır ve zamanlayıcıyı çalıştırır."""
        self.startup()
        print("\n...CTRL+C ile çıkış yapabilirsiniz...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\nINFO: Program sonlandırılıyor.")

if __name__ == "__main__":
    station = MeteorologyStation(config_path=CONFIG_PATH, db_path=DB_PATH)
    station.start()