import serial
import time
import glob
import re
from smbus2 import SMBus

class SensorManager:
    """
    Sensörleri dinamik olarak keşfeder, bağlar ve okur.
    """
    def __init__(self, config):
        """
        Args:
            config (dict): Önceden yüklenmiş yapılandırma sözlüğü.
        """
        print("INFO: SensorManager başlatılıyor...")
        self.config = config
        self.sensor_definitions = self.config.get('sensors', {})
        self.serial_port_pattern = self.config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {}
        self.active_connections = {}

    def find_and_assign_sensors(self):
        """
        Sistemdeki seri portları tarar, sensörleri kimliklerine göre atar.
        """
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        print(f"INFO: Taranacak port deseni: {self.serial_port_pattern}")
        available_ports = glob.glob(self.serial_port_pattern)
        if not available_ports:
            print(f"WARNING: Sistemde '{self.serial_port_pattern}' deseniyle eşleşen port bulunamadı.")
        
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
                        print(f"  -> WARNING: '{port}' portundan zaman aşımında veri okunamadı.")
                        continue
                    found_match = False
                    for name, regex in regex_map.items():
                        if regex.search(line):
                            print(f"  -> SUCCESS: Bu veri '{name}' sensörüne ait. Atama yapılıyor.")
                            self.assigned_ports[name] = port
                            found_match = True
                            break
                    if not found_match:
                        print(f"  -> WARNING: Okunan veri tanımlı desenle eşleşmedi.")
            except serial.SerialException as e:
                print(f"  -> ERROR: '{port}' portu açılamadı: {e}")
            except Exception as e:
                print(f"  -> ERROR: '{port}' portunda beklenmedik hata: {e}")
        
        serial_enabled_names = {name for name, d in self.sensor_definitions.items() if d.get('enabled') and 'identifier_pattern' in d}
        found_sensor_names = set(self.assigned_ports.keys())
        if not serial_enabled_names.issubset(found_sensor_names):
            missing_sensors = serial_enabled_names - found_sensor_names
            print(f"ERROR: Şu sensörler bulunamadı: {', '.join(missing_sensors)}. Lütfen bağlantıları kontrol edin.")

    def get_assigned_ports(self):
        """
        Atanmış portların bir kopyasını döndürür. BU FONKSİYON EKLENDİ.
        """
        return self.assigned_ports

    def _connect_to_serial_sensors(self):
        """Atanan portlara seri bağlantı açar."""
        for name, port in self.assigned_ports.items():
            if name not in self.active_connections:
                try:
                    baudrate = self.sensor_definitions[name].get('baudrate', 9600)
                    ser = serial.Serial(port, baudrate, timeout=2)
                    self.active_connections[name] = ser
                except serial.SerialException as e:
                    print(f"ERROR: '{name}' sensörüne bağlanılamadı ({port}): {e}")

    def _disconnect_serial_sensors(self):
        """Tüm açık seri bağlantıları kapatır."""
        for ser_conn in self.active_connections.values():
            ser_conn.close()
        self.active_connections = {}

    def _read_serial_sensors(self):
        """Bağlı tüm seri sensörlerden veri okur."""
        raw_readings = {}
        self._connect_to_serial_sensors()
        for name, ser_conn in self.active_connections.items():
            try:
                ser_conn.reset_input_buffer()
                time.sleep(0.5)
                raw_line = ser_conn.readline()
                if raw_line:
                    line = raw_line.decode('utf-8', errors='ignore').strip()
                    raw_readings[name] = line
            except serial.SerialException as e:
                print(f"ERROR: '{name}' sensörünü okurken hata: {e}")
        self._disconnect_serial_sensors()
        return raw_readings

    def _read_sht3x(self):
        """SHT3X I2C sensöründen okuma yapar."""
        sht_config = self.sensor_definitions.get('temperature_humidity', {})
        if not sht_config.get('enabled'):
            return {}
        try:
            bus = SMBus(sht_config.get('i2c_bus', 1))
            addr = sht_config.get('i2c_address', 0x44)
            bus.write_i2c_block_data(addr, 0x2C, [0x06])
            time.sleep(0.1)
            data = bus.read_i2c_block_data(addr, 0x00, 6)
            bus.close()
            temp_raw = (data[0] << 8) | data[1]
            temp_c = -45 + (175 * temp_raw / 65535)
            hum_raw = (data[3] << 8) | data[4]
            hum_percent = 100 * hum_raw / 65535
            return {'temperature_c': temp_c, 'humidity_percent': hum_percent}
        except Exception as e:
            print(f"ERROR: I2C (Sıcaklık/Nem) sensörü okunamadı: {e}")
            return {}

    def read_all_sensors(self):
        """
        Tüm aktif sensörlerden (seri ve I2C) okuma yapar.
        """
        all_readings = self._read_serial_sensors()
        i2c_readings = self._read_sht3x()
        all_readings.update(i2c_readings)
        return all_readings