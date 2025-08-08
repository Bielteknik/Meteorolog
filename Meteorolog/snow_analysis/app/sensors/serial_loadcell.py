import serial
import re
import time
from .base_sensor import BaseSensor

class SerialLoadcell(BaseSensor):
    """Seri porttan '=' ile başlayan ağırlık verisi gönderen yük hücresi için plugin."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.baudrate = int(self.config.get("baudrate", 9600))

    @staticmethod
    def check_fingerprint(data_sample: str, config: dict) -> bool:
        """Parmak izi kontrolü: Gelen veri '= 12.34' formatında mı?"""
        fingerprint_regex = config.get("fingerprint_regex", "^=\\s*(-?\\d+\\.\\d+)")
        try:
            for line in data_sample.strip().split('\n'):
                if re.search(fingerprint_regex, line.strip()):
                    return True
            return False
        except Exception:
            return False

    def connect(self, port: str) -> bool:
        self.port = port
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(2)
            if self.connection.is_open:
                print(f"✅ 'SerialLoadcell' ({self.name}) {self.port} portuna başarıyla bağlandı.")
                return True
        except serial.SerialException as e:
            print(f"❌ 'SerialLoadcell' ({self.name}) {self.port} portuna bağlanamadı: {e}")
            return False
        return False

    def read(self) -> float | None:
        """Sensörden ağırlık verisini (kg) okur."""
        if not (self.connection and self.connection.is_open):
            return None
        
        try:
            self.connection.reset_input_buffer()
            line = self.connection.readline().decode('utf-8').strip()
            
            match = re.search(r"=\s*(-?\d+\.\d+)", line)
            if match:
                return float(match.group(1))
            return None
        except (serial.SerialException, ValueError, TypeError) as e:
            print(f"❌ {self.name} sensöründen okuma hatası: {e}")
            return None