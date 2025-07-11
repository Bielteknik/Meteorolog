import serial
import time
import glob
import re
from smbus2 import SMBus

class SensorManager:
    def __init__(self, config):
        self.config = config
        self.sensor_definitions = self.config.get('sensors', {})
        self.serial_port_pattern = self.config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {}
        self.active_connections = {}
        print("INFO: SensorManager başlatıldı.")

    def find_and_assign_sensors(self):
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        available_ports = glob.glob(self.serial_port_pattern)
        print(f"INFO: Bulunan potansiyel portlar: {available_ports}")

        regex_map = { name: re.compile(d['identifier_pattern']) for name, d in self.sensor_definitions.items() if d.get('enabled') and 'identifier_pattern' in d }

        for port in available_ports:
            print(f"\nINFO: '{port}' portu analiz ediliyor...")
            try:
                with serial.Serial(port, 9600, timeout=1) as ser:
                    time.sleep(2)
                    ser.reset_input_buffer()
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line: time.sleep(1); line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    print(f"  -> Okunan veri: '{line}'")
                    if not line: continue
                    
                    for name, regex in regex_map.items():
                        if regex.search(line):
                            print(f"  -> SUCCESS: Bu veri '{name}' sensörüne ait. Atama yapılıyor.")
                            self.assigned_ports[name] = port
                            break
            except Exception as e: print(f"  -> ERROR: Port analizi hatası: {e}")
        
        enabled_serial = {name for name, d in self.sensor_definitions.items() if d.get('enabled') and 'identifier_pattern' in d}
        if not enabled_serial.issubset(set(self.assigned_ports.keys())):
            missing = enabled_serial - set(self.assigned_ports.keys())
            print(f"ERROR: Şu seri sensörler bulunamadı: {', '.join(missing)}")

    def get_assigned_ports(self):
        return self.assigned_ports

    def _read_serial_sensors(self):
        readings = {}
        for name, port in self.assigned_ports.items():
            try:
                with serial.Serial(port, 9600, timeout=2) as ser:
                    time.sleep(0.1)
                    ser.reset_input_buffer()
                    line = ser.readline().decode('utf-8', 'ignore').strip()
                    if line:
                        readings[name] = line
                        print(f"INFO: '{name}' sensöründen okundu: '{line}'")
            except Exception as e: print(f"ERROR: '{name}' okunurken hata: {e}")
        return readings

    def _read_sht3x(self):
        sht_config = self.sensor_definitions.get('temperature_humidity')
        if not sht_config or not sht_config.get('enabled'): return {}
        try:
            with SMBus(sht_config.get('i2c_bus', 1)) as bus:
                addr = sht_config.get('i2c_address', 0x44)
                bus.write_i2c_block_data(addr, 0x2C, [0x06])
                time.sleep(0.1)
                data = bus.read_i2c_block_data(addr, 0x00, 6)
                temp = -45 + (175 * ((data[0] << 8) | data[1]) / 65535.0)
                hum = 100 * ((data[3] << 8) | data[4]) / 65535.0
                print(f"INFO: I2C sensöründen okundu: Temp={temp:.1f}C, Hum={hum:.1f}%")
                return {'temperature_c': temp, 'humidity_percent': hum}
        except Exception as e:
            print(f"ERROR: I2C sensörü okunamadı: {e}")
            return {}

    def read_all_sensors(self):
        all_readings = self._read_serial_sensors()
        i2c_readings = self._read_sht3x()
        all_readings.update(i2c_readings)
        return all_readings