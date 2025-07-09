import serial
import time
from smbus2 import SMBus
from typing import List, Dict
import logging

from app.config import settings
from app.sensors.parsers import parse_height, parse_weight

# Her modülün başına bu iki satırı ekliyoruz
logger = logging.getLogger(__name__)

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
        """
        Verilen portu daha sabırlı bir şekilde koklayarak hangi sensöre ait olduğunu bulur.
        Birkaç kez okuma denemesi yapar.
        """
        logger.debug(f"Probing port: '{port_name}'")
        try:
            # Portu daha uzun bir timeout ile açıyoruz
            with serial.Serial(port_name, settings.SERIAL_BAUD_RATE, timeout=1.0) as ser:
                # Buffer'ı temizle
                ser.reset_input_buffer()
                time.sleep(0.2) # Stabilizasyon için kısa bekleme
    
                # Birkaç saniye boyunca veri okumayı dene
                for _ in range(3): # En fazla 3 deneme
                    time.sleep(0.7) # Veri gelmesi için daha uzun bekle
                    
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        
                        # Yükseklik sensörü olarak test et
                        if parse_height(data) is not None:
                            logger.info(f"Port '{port_name}' identified as HEIGHT sensor.")
                            return "height"
                        
                        # Ağırlık sensörü olarak test et (readline() ile daha güvenli)
                        lines = data.split(b'\n')
                        for line in lines:
                            if parse_weight(line) is not None:
                                logger.info(f"Port '{port_name}' identified as WEIGHT sensor.")
                                return "weight"
    
        except serial.SerialException as e:
            logger.warning(f"Could not open port '{port_name}' during probing: {e}")
            pass # Port meşgul veya açılamıyor
        
        logger.debug(f"Could not determine sensor type for port '{port_name}'.")
        return None

    def discover_ports(self):
        """Sistemdeki /dev/ttyUSB portlarını tarayarak sensörleri bulur."""
        logger.info("🔎 Discovering sensor ports...")
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

        if not self.height_port:
            logger.warning("⚠️ Height sensor port NOT FOUND!")
        if not self.weight_port:
            logger.warning("⚠️ Weight sensor port NOT FOUND!")

    def connect(self):
        """Tespit edilen portlara ve I2C cihazına bağlanır."""
        logger.info("🔌 Connecting to sensors...")
        # Mesafe sensörü
        if self.height_port and not self.is_height_connected:
            try:
                self.height_ser = serial.Serial(self.height_port, settings.SERIAL_BAUD_RATE, timeout=settings.SERIAL_READ_TIMEOUT_S)
                self.is_height_connected = True
                logger.info(f"✔ Height sensor connected: {self.height_port}")
            except serial.SerialException as e:
                logger.error(f"❌ Failed to connect to height sensor ({self.height_port}): {e}")

        # Ağırlık sensörü
        if self.weight_port and not self.is_weight_connected:
            try:
                self.weight_ser = serial.Serial(self.weight_port, settings.SERIAL_BAUD_RATE, timeout=settings.SERIAL_READ_TIMEOUT_S)
                self.is_weight_connected = True
                logger.info(f"✔ Weight sensor connected: {self.weight_port}")
            except serial.SerialException as e:
                logger.error(f"❌ Failed to connect to weight sensor ({self.weight_port}): {e}")
        
        # Sıcaklık/Nem sensörü (I2C)
        if not self.is_temp_hum_connected:
            try:
                self.i2c_bus = SMBus(settings.I2C_BUS)
                # Basit bir test komutu göndererek cihazın varlığını kontrol et
                self.i2c_bus.write_byte(settings.I2C_SHT3X_ADDRESS, 0x00)
                self.is_temp_hum_connected = True
                logger.info(f"✔ Temp/Humidity sensor connected: I2C-{settings.I2C_BUS}")
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error(f"❌ Failed to connect to Temp/Humidity sensor (I2C): {e}")

    def disconnect(self):
        """Tüm aktif bağlantıları güvenli bir şekilde kapatır."""
        logger.info("🔌 Disconnecting all sensors...")
        if self.height_ser and self.height_ser.is_open:
            self.height_ser.close()
            self.is_height_connected = False
            logger.debug("Height sensor connection closed.")
        if self.weight_ser and self.weight_ser.is_open:
            self.weight_ser.close()
            self.is_weight_connected = False
            logger.debug("Weight sensor connection closed.")
        if self.i2c_bus:
            self.i2c_bus.close()
            self.is_temp_hum_connected = False
            logger.debug("I2C bus connection closed.")
        logger.info("✔ All connections closed.")