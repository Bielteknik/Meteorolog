# Dosya: Meteorolog/src/main.py

import time
from datetime import datetime
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler

# Modüller
from modules.sensor_manager import SensorManager
from modules.data_processor import DataProcessor
from modules.storage_manager import StorageManager
from modules.communication_manager import CommunicationManager
from modules.rich_display import RichDisplay # YENİ

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

        # Sistem durumunu tutacak merkezi bir sözlük
        self.system_status = {
            'sensors': {},
            'i2c_sensor': {'connected': False, 'detail': 'Henüz kontrol edilmedi.'},
            'last_collection': {},
            'last_api_send': {},
            'next_job': {}
        }
        
        # Modülleri başlat
        self.sensor_manager = SensorManager(self.config)
        self.data_processor = DataProcessor(self.config)
        self.storage_manager = StorageManager(db_path)
        self.comm_manager = CommunicationManager(self.config)
        
    def startup(self):
        """Sistemin başlangıç prosedürleri ve ilk durum kontrolü."""
        print("INFO: Sensörler keşfediliyor ve ilk durum paneli hazırlanıyor...")
        self.sensor_manager.find_and_assign_sensors()
        self._update_status_dashboard() # İlk dashboard'u göster

    def _update_status_dashboard(self, next_job_info=None):
        """Sistem durumu sözlüğünü günceller ve paneli yazdırır."""
        # Seri sensör durumlarını güncelle
        assigned_ports = self.sensor_manager.get_assigned_ports()
        for name, definition in self.config['sensors'].items():
            if 'identifier_pattern' in definition: # Sadece seri sensörler
                self.system_status['sensors'][name] = {
                    'connected': name in assigned_ports,
                    'detail': f"Port: {assigned_ports.get(name, 'Bulunamadı')}"
                }
        
        # I2C sensör durumunu güncelle (Bu kısım read_all_sensors içinde güncellenecek)
        # Şimdilik varsayılan kalıyor.
        
        if next_job_info:
             self.system_status['next_job'] = {
                'name': next_job_info.get('name'),
                'time': next_job_info.get('time').strftime('%H:%M:%S')
            }

        self.display.print_status_dashboard(self.system_status)

    def run_collection_cycle(self):
        """Zamanlayıcı tarafından periyodik olarak çalıştırılacak ana görev."""
        self.display.print_collection_header()

        # 1. VERİ TOPLAMA
        raw_data = self.sensor_manager.read_all_sensors()
        self.system_status['last_collection'] = {
            'status': 'Success' if raw_data else 'Failure',
            'time': datetime.now().strftime('%H:%M:%S')
        }
        # I2C durumunu anlık olarak güncelle
        self.system_status['i2c_sensor']['connected'] = 'temperature_c' in raw_data
        self.system_status['i2c_sensor']['detail'] = "Veri okundu" if 'temperature_c' in raw_data else "Bağlantı hatası"
        
        # 2. VERİ İŞLEME
        processed_data = self.data_processor.process_reading_data(raw_data)
        
        # 3. VERİ SAKLAMA
        if processed_data:
            processed_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.storage_manager.save_reading(processed_data)
        
        self.display.print_collection_result(processed_data)
        self._update_status_dashboard() # Her döngü sonunda durumu tekrar göster

    def run_api_send_cycle(self):
        """API gönderme görevi."""
        latest_data = self.storage_manager.get_latest_reading()
        if latest_data:
            api_payload = self.comm_manager.format_data_for_api(latest_data)
            success = self.comm_manager.send_data(api_payload)
            self.system_status['last_api_send'] = {
                'status': 'Success' if success else 'Failure',
                'time': datetime.now().strftime('%H:%M:%S')
            }
        self._update_status_dashboard()


if __name__ == "__main__":
    station = MeteorologyStation(config_path=CONFIG_PATH, db_path=DB_PATH)
    station.startup() # İlk keşif ve panel
    
    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    
    collect_interval = station.config['scheduler']['data_collection_interval_minutes']
    api_interval = station.config['scheduler']['api_send_interval_minutes']
    
    # Görevleri zamanla ve hemen bir kez çalıştır
    scheduler.add_job(station.run_collection_cycle, 'interval', minutes=collect_interval, id='collect_job', name="Veri Toplama")
    scheduler.add_job(station.run_api_send_cycle, 'interval', minutes=api_interval, id='api_job', name="API Gönderim")

    print(f"\nINFO: Veri toplama görevi her {collect_interval} dakikada bir çalışacak.")
    print(f"INFO: API gönderme görevi her {api_interval} dakikada bir çalışacak.")
    print("...CTRL+C ile çıkış yapabilirsiniz...")
    
    # İlk döngüyü manuel olarak tetikle
    print("✨ Sistem aktif. İlk döngü hemen başlatılıyor...")
    station.run_collection_cycle()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nINFO: Program sonlandırılıyor.")