import serial
import time
import glob
import re
import yaml

class SensorManager:
    def __init__(self, config):
        """
        Args:
            config (dict): Önceden yüklenmiş yapılandırma sözlüğü.
        """
        print("INFO: SensorManager başlatılıyor...")
        # Artık dosyayı burada açmıyoruz, hazır config'i alıyoruz.
        self.config = config
        
        self.sensor_definitions = self.config.get('sensors', {})
        self.serial_port_pattern = self.config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {}
        self.active_connections = {}

    def find_and_assign_sensors(self):
        # Bu fonksiyon bir önceki adımdaki ile aynı, değişmedi.
        # ... (Önceki adımdaki kodun tamamı buraya gelecek)
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        print(f"INFO: Taranacak port deseni: {self.serial_port_pattern}")
        available_ports = glob.glob(self.serial_port_pattern)
        if not available_ports:
            print(f"WARNING: Sistemde '{self.serial_port_pattern}' deseniyle eşleşen hiçbir seri port bulunamadı.")
        print(f"INFO: Bulunan potansiyel portlar: {available_ports}")
        regex_map = {
            name: re.compile(definition['identifier_pattern'])
            for name, definition in self.sensor_definitions.items()
            if definition.get('enabled', False) and 'identifier_pattern' in definition
        }
        for port in available_ports:
            print(f"\nINFO: '{port}' portu analiz ediliyor...")
            baudrate = 9600
            try:
                with serial.Serial(port, baudrate, timeout=1) as ser:
                    time.sleep(2)
                    ser.reset_input_buffer()
                    print("  -> Anlamlı veri bekleniyor (en fazla 5 saniye)...")
                    start_time = time.time()
                    line = ""
                    while time.time() - start_time < 5:
                        raw_line = ser.readline()
                        if raw_line:
                            line = raw_line.decode('utf-8', errors='ignore').strip()
                            if line: break
                    print(f"  -> Okunan veri: '{line}'")
                    if not line:
                        print(f"  -> WARNING: '{port}' portundan zaman aşımı süresince veri okunamadı. Atlanıyor.")
                        continue
                    found_match = False
                    for name, regex in regex_map.items():
                        if regex.search(line):
                            if name in self.assigned_ports:
                                print(f"  -> CRITICAL: Çakışma! '{name}' sensörü zaten atanmış.")
                            else:
                                print(f"  -> SUCCESS: Bu veri '{name}' sensörüne ait. Atama yapılıyor.")
                                self.assigned_ports[name] = port
                                found_match = True
                                break 
                    if not found_match:
                        print(f"  -> WARNING: Okunan veri, tanımlı hiçbir sensör deseniyle eşleşmedi.")
            except serial.SerialException as e:
                print(f"  -> ERROR: '{port}' portu açılamadı veya okunamadı: {e}")
            except Exception as e:
                print(f"  -> ERROR: '{port}' portunda beklenmedik hata: {e}")
        serial_enabled_names = {name for name, d in self.sensor_definitions.items() if d.get('enabled') and 'identifier_pattern' in d}
        found_sensor_names = set(self.assigned_ports.keys())
        if serial_enabled_names.issubset(found_sensor_names):
            print("\nSUCCESS: Tüm aktif seri port sensörleri başarıyla atandı.")
            return True
        else:
            missing_sensors = serial_enabled_names - found_sensor_names
            if missing_sensors:
                print(f"\nERROR: Şu sensörler bulunamadı: {', '.join(missing_sensors)}. Lütfen bağlantıları kontrol edin.")
            return False

    def _connect_to_sensors(self):
        """Atanan portlara seri bağlantı açar."""
        for name, port in self.assigned_ports.items():
            if name not in self.active_connections:
                try:
                    baudrate = self.sensor_definitions[name].get('baudrate', 9600)
                    ser = serial.Serial(port, baudrate, timeout=2)
                    self.active_connections[name] = ser
                    print(f"INFO: '{name}' sensörüne bağlantı açıldı: {port}")
                except serial.SerialException as e:
                    print(f"ERROR: '{name}' sensörüne bağlanılamadı ({port}): {e}")
        return len(self.active_connections) > 0

    def _disconnect_sensors(self):
        """Tüm açık seri bağlantıları kapatır."""
        for name, ser_conn in self.active_connections.items():
            ser_conn.close()
            print(f"INFO: '{name}' sensörüyle bağlantı kapatıldı.")
        self.active_connections = {}

    def read_all_sensors(self):
        """
        Tüm bağlı sensörlerden tek bir okuma seti toplar.
        Returns:
            dict: {'distance': 'R2815', 'weight': '= 12.34C0'} gibi ham veriler.
        """
        raw_readings = {}
        if not self._connect_to_sensors():
            print("WARNING: Okunacak aktif sensör bağlantısı yok.")
            return raw_readings

        for name, ser_conn in self.active_connections.items():
            try:
                # Buffer'ı temizle ve taze veri bekle
                ser_conn.reset_input_buffer()
                time.sleep(0.5)
                # Anlamlı bir veri gelene kadar bekle
                start_time = time.time()
                line = ""
                while time.time() - start_time < 5: # 5 saniye timeout
                    raw_line = ser_conn.readline()
                    if raw_line:
                        line = raw_line.decode('utf-8', errors='ignore').strip()
                        if line:
                            raw_readings[name] = line
                            break
                if not line:
                     print(f"WARNING: '{name}' sensöründen veri okunamadı (timeout).")
            except serial.SerialException as e:
                print(f"ERROR: '{name}' sensörünü okurken hata: {e}")
        
        self._disconnect_sensors()
        return raw_readings