import glob
import re
import serial
import time
from smbus2 import SMBus

class SensorManager:
    def __init__(self, config):
        self.config = config; self.sensors = config.get('sensors', {})
        self.serial_pattern = config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {}
        print("INFO: SensorManager başlatıldı.")
    def find_and_assign_sensors(self):
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        regex_map = {n: re.compile(d['identifier_pattern']) for n, d in self.sensors.items() if d.get('enabled') and 'identifier_pattern' in d}
        for port in (ports := glob.glob(self.serial_pattern)):
            print(f"\nINFO: '{port}' portu analiz ediliyor...")
            try:
                with serial.Serial(port, 9600, timeout=1) as ser:
                    time.sleep(1); ser.reset_input_buffer()
                    line = ser.readline().decode('utf-8', 'ignore').strip()
                    if not line: time.sleep(1); line = ser.readline().decode('utf-8', 'ignore').strip()
                    print(f"  -> Okunan veri: '{line}'")
                    if not line: continue
                    for name, regex in regex_map.items():
                        if regex.search(line): self.assigned_ports[name] = port; print(f"  -> SUCCESS: '{name}' atandı."); break
            except Exception as e: print(f"  -> ERROR: Port analizi hatası: {e}")
        print(f"INFO: Bulunan portlar: {ports}, Atananlar: {self.assigned_ports}")
    def get_assigned_ports(self): return self.assigned_ports
    def _read_serial_sensors(self):
        readings = {}
        for name, port in self.assigned_ports.items():
            try:
                with serial.Serial(port, 9600, timeout=2) as ser:
                    ser.reset_input_buffer()
                    if line := ser.readline().decode('utf-8', 'ignore').strip(): readings[name] = line
            except Exception as e: print(f"ERROR: '{name}' okunurken hata: {e}")
        return readings
    def _read_sht3x(self):
        if not (s_conf := self.sensors.get('temperature_humidity')) or not s_conf.get('enabled'): return {}
        try:
            with SMBus(s_conf.get('i2c_bus', 1)) as bus:
                addr = s_conf.get('i2c_address', 0x44)
                bus.write_i2c_block_data(addr, 0x2C, [0x06]); time.sleep(0.1)
                d = bus.read_i2c_block_data(addr, 0x00, 6)
                temp = -45 + (175 * ((d[0] << 8) | d[1]) / 65535.0)
                hum = 100 * ((d[3] << 8) | d[4]) / 65535.0
                return {'temperature_c': temp, 'humidity_percent': hum}
        except Exception as e: print(f"ERROR: I2C sensörü okunamadı: {e}"); return {}
    def read_all_sensors(self):
        data = self._read_serial_sensors(); data.update(self._read_sht3x()); return data
    def shutdown(self): print("INFO: SensorManager kaynakları temizlendi.")