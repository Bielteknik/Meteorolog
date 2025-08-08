import serial
import re
import time
from .base_sensor import BaseSensor

class DFRobotUltrasonic(BaseSensor):
    """DFRobot URM09 Ultrasonik Yükseklik Sensörü için plugin."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.baudrate = int(self.config.get("baudrate", 9600))
        self.zero_point_mm = float(self.config.get("zero_point_mm", 0))

    @staticmethod
    def check_fingerprint(data_sample: str, config: dict) -> bool:
        """Parmak izi kontrolü: Gelen veri sadece 3-5 basamaklı bir sayı mı?"""
        fingerprint_regex = config.get("fingerprint_regex", "^\\d{3,5}$")
        try:
            # Gelen veri örneğinin her satırını kontrol et
            for line in data_sample.strip().split('\n'):
                if re.match(fingerprint_regex, line.strip()):
                    return True # Eşleşme bulundu, bu sensör bu olabilir.
            return False
        except Exception:
            return False

    def connect(self, port: str) -> bool:
        """Belirtilen seri porta bağlanmayı dener."""
        self.port = port
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(2) # Portun ve sensörün "oturması" için kritik bekleme
            if self.connection.is_open:
                print(f"✅ 'DFRobotUltrasonic' ({self.name}) {self.port} portuna başarıyla bağlandı.")
                return True
        except serial.SerialException as e:
            print(f"❌ 'DFRobotUltrasonic' ({self.name}) {self.port} portuna bağlanamadı: {e}")
            return False
        return False

    def read(self) -> float | None:
        """Sensörden mesafe verisini (mm) okur."""
        if not (self.connection and self.connection.is_open):
            print(f"⚠️ {self.name} sensörü bağlı değil, okuma atlanıyor.")
            return None
        
        try:
            # Olası kirli veriyi temizlemek için buffer'ı boşalt
            self.connection.reset_input_buffer()
            line = self.connection.readline().decode('utf-8').strip()
            
            if line:
                return float(line)
            return None
        except (serial.SerialException, ValueError, TypeError) as e:
            print(f"❌ {self.name} sensöründen okuma hatası: {e}")
            return None
