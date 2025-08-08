from smbus2 import SMBus, i2c_msg
import time
from .base_sensor import BaseSensor

class SHT3xI2C(BaseSensor):
    """SHT3x (ve benzeri) I2C sıcaklık/nem sensörleri için plugin."""

    def __init__(self, config: dict):
        super().__init__(config)
        # I2C adresi onaltılık (hex) veya onluk (decimal) formatta olabilir.
        self.i2c_address = int(self.config.get("i2c_address"), 16)

    @staticmethod
    def check_fingerprint(data_sample: str, config: dict) -> bool:
        """I2C sensörleri port taraması ile bulunmaz, adresleri ile bulunur."""
        # Bu yüzden bu metodun seri sensör keşfinde rolü yoktur.
        return False

    def connect(self, port: str) -> bool:
        """
        I2C için 'port' aslında I2C veriyolunun numarasıdır (genellikle '1').
        Bağlantı, adreste bir cihaz olup olmadığını kontrol ederek yapılır.
        """
        self.port = port # port = "1"
        bus_number = int(self.port)
        try:
            self.connection = SMBus(bus_number)
            # Adrese basit bir yazma işlemi göndererek cihazın varlığını kontrol et.
            self.connection.write_byte(self.i2c_address, 0x00)
            print(f"✅ 'SHT3xI2C' ({self.name}) I2C-{bus_number} veriyolunda {hex(self.i2c_address)} adresinde bulundu.")
            return True
        except Exception as e:
            # PermissionError veya diğer I2C hataları
            self.connection = None
            print(f"❌ 'SHT3xI2C' ({self.name}) {hex(self.i2c_address)} adresinde bulunamadı: {e}")
            return False
        return False

    def read(self) -> tuple[float, float] | None:
        """Sensörden sıcaklık (°C) ve nem (%RH) okur."""
        if not self.connection:
            return None
        
        try:
            # SHT31 için ölçüm komutu
            write = i2c_msg.write(self.i2c_address, [0x2C, 0x06])
            read = i2c_msg.read(self.i2c_address, 6)
            
            self.connection.i2c_rdwr(write)
            time.sleep(0.1) # Ölçüm için kısa bir bekleme
            self.connection.i2c_rdwr(read)
            
            data = list(read)
            temp = -45 + (175 * (data[0] * 256 + data[1])) / 65535.0
            humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
            
            return (temp, humidity)
        except Exception as e:
            print(f"❌ {self.name} sensöründen okuma hatası: {e}")
            return None
    
    def disconnect(self):
        """SMBus bağlantısını kapatır."""
        if self.connection:
            self.connection.close()
            print(f"🔌 {self.name} bağlantısı kapatıldı.")