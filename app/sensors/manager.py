import serial
import time
from smbus2 import SMBus
from typing import List, Dict

from app.config import settings
from app.sensors.parsers import parse_height, parse_weight

class SensorManager:
    """Sensör bağlantılarını (Serial, I2C) yönetir."""
    def __init__(self):
        # Bağlantı nesneleri
        self.height_ser: serial.Serial | None = None
        self.weight_ser: serial.Serial | None = None
        self.i2c_bus: SMBus | None = None

        # Bağlantı durumu
        self.is_height_connected: bool = False
        self.is_weight_connected: bool = False
        self.is_temp_hum_connected: bool = False

        # Tespit edilen portlar
        self.height_port: str | None = None
        self.weight_port: str | None = None

    def _probe_port(self, port_name: str) -> str | None:
        """Verilen portu koklayarak hangi sensöre ait olduğunu bulur."""
        # Yükseklik sensörü olarak test et
        try:
            with serial.Serial(port_name, settings.SERIAL_BAUD_RATE, timeout=settings.SERIAL_PROBE_TIMEOUT_S) as ser:
                time.sleep(0.5) # Veri gelmesi için bekle
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    if parse_height(data) is not None:
                        print(f"✅ '{port_name}' yükseklik sensörü olarak tanımlandı.")
                        return "height"
        except serial.SerialException:
            pass # Port meşgul veya açılamıyor

        # Ağırlık sensörü olarak test et
        try:
            with serial.Serial(port_name, settings.SERIAL_BAUD_RATE, timeout=settings.SERIAL_PROBE_TIMEOUT_S) as ser:
                time.sleep(0.5) # Veri gelmesi için bekle
                if ser.in_waiting > 0:
                    line = ser.readline()
                    if parse_weight(line) is not None:
                        print(f"✅ '{port_name}' ağırlık sensörü olarak tanımlandı.")
                        return "weight"
        except serial.SerialException:
            pass # Port meşgul veya açılamıyor

        return None

    def discover_ports(self):
        """Sistemdeki /dev/ttyUSB portlarını tarayarak sensörleri bulur."""
        print("🔎 Sensör portları aranıyor...")
        potential_ports = [f'/dev/ttyUSB{i}' for i in range(4)]
        identified_ports: Dict[str, str] = {} # {'height': '/dev/ttyUSB1', ...}

        for port in potential_ports:
            try: # Portun var olup olmadığını kontrol et
                s = serial.Serial(port)
                s.close()
            except serial.SerialException:
                continue # Port yok, diğerine geç

            if len(identified_ports) == 2: break # İkisi de bulunduysa döngüden çık

            sensor_type = self._probe_port(port)
            if sensor_type and sensor_type not in identified_ports:
                identified_ports[sensor_type] = port

        self.height_port = identified_ports.get("height")
        self.weight_port = identified_ports.get("weight")

        if not self.height_port: print("⚠️ Yükseklik sensörü portu bulunamadı!")
        if not self.weight_port: print("⚠️ Ağırlık sensörü portu bulunamadı!")

    def connect(self):
        """Tespit edilen portlara ve I2C cihazına bağlanır."""
        print("🔌 Sensörlere bağlanılıyor...")
        # Mesafe sensörü
        if self.height_port and not self.is_height_connected:
            try:
                self.height_ser = serial.Serial(self.height_port, settings.SERIAL_BAUD_RATE, timeout=settings.SERIAL_READ_TIMEOUT_S)
                self.is_height_connected = True
                print(f"✔ Mesafe sensörü bağlandı: {self.height_port}")
            except serial.SerialException as e:
                print(f"❌ Mesafe sensörü ({self.height_port}) bağlanamadı: {e}")

        # Ağırlık sensörü
        if self.weight_port and not self.is_weight_connected:
            try:
                self.weight_ser = serial.Serial(self.weight_port, settings.SERIAL_BAUD_RATE, timeout=settings.SERIAL_READ_TIMEOUT_S)
                self.is_weight_connected = True
                print(f"✔ Ağırlık sensörü bağlandı: {self.weight_port}")
            except serial.SerialException as e:
                print(f"❌ Ağırlık sensörü ({self.weight_port}) bağlanamadı: {e}")
        
        # Sıcaklık/Nem sensörü (I2C)
        if not self.is_temp_hum_connected:
            try:
                self.i2c_bus = SMBus(settings.I2C_BUS)
                # Basit bir test komutu göndererek cihazın varlığını kontrol et
                self.i2c_bus.write_byte(settings.I2C_SHT3X_ADDRESS, 0x00)
                self.is_temp_hum_connected = True
                print(f"✔ Sıcaklık/Nem sensörü bağlandı: I2C-{settings.I2C_BUS}")
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"❌ Sıcaklık/Nem sensörü (I2C) bağlanamadı: {e}")


    def disconnect(self):
        """Tüm aktif bağlantıları güvenli bir şekilde kapatır."""
        print("🔌 Bağlantılar kapatılıyor...")
        if self.height_ser and self.height_ser.is_open:
            self.height_ser.close()
            self.is_height_connected = False
        if self.weight_ser and self.weight_ser.is_open:
            self.weight_ser.close()
            self.is_weight_connected = False
        if self.i2c_bus:
            self.i2c_bus.close()
            self.is_temp_hum_connected = False
        print("✔ Tüm bağlantılar kapatıldı.")