import time
import logging
from typing import Dict

# Bu, kodumuzun temelini oluşturur.
from app.config import settings

# --- Platforma Özel Kütüphaneleri Koşullu Olarak Yükleme ---
# Eğer Geliştirici Modu aktif değilse (yani Linux'ta çalışıyorsa),
# gerçek donanım kütüphanelerini import etmeye çalış.
if not settings.DEV_MODE:
    try:
        import serial
        from smbus2 import SMBus
    except ImportError:
        logging.critical("Linux modunda gerekli 'pyserial' veya 'smbus2' kütüphaneleri bulunamadı.")
        # Programın devam etmemesi için sahte sınıflar burada tanımlanmıyor.
        # Bu durumda bir hata ile çıkması daha doğru.
else:
    # Geliştirici Modu (Windows) aktif ise, bu kütüphaneler hata vereceği için
    # onların yerine geçen "sahte" (dummy) sınıflar oluşturuyoruz.
    # Bu, kodun geri kalanının donanım olmadan da çalışmasını sağlar.
    logging.warning("DEV_MODE is active. Using dummy sensor classes.")

    class serial:
        class Serial:
            """Sahte Seri Port Sınıfı"""
            def __init__(self, port=None, baudrate=None, timeout=None):
                self.port = port
                self.is_open = True
                logging.info(f"[DEV_MODE] Dummy Serial connection created for port: {port}")
            def close(self): self.is_open = False; logging.info(f"[DEV_MODE] Dummy Serial connection closed for port: {self.port}")
            def read(self, size=1): return b''
            def readline(self): return b''
            def reset_input_buffer(self): pass
            @property
            def in_waiting(self): return 0
        
        class SerialException(Exception): pass

    class SMBus:
        """Sahte I2C Bus Sınıfı"""
        def __init__(self, bus=None):
            logging.info(f"[DEV_MODE] Dummy SMBus created for bus: {bus}")
        def write_i2c_block_data(self, addr, cmd, data): pass
        def read_i2c_block_data(self, addr, cmd, length): return [0] * length
        def write_byte(self, addr, val): pass
        def close(self): logging.info("[DEV_MODE] Dummy SMBus connection closed.")


# Logger'ı bu modül için tanımla
logger = logging.getLogger(__name__)


class SensorManager:
    """
    Sensör bağlantılarını (Serial, I2C) yönetir.
    Geliştirici Modu (DEV_MODE) ile platform bağımsız çalışır.
    """
    def __init__(self):
        self.height_ser: "serial.Serial" | None = None
        self.weight_ser: "serial.Serial" | None = None
        self.i2c_bus: "SMBus" | None = None

        self.is_height_connected: bool = False
        self.is_weight_connected: bool = False
        self.is_temp_hum_connected: bool = False

        self.height_port: str | None = None
        self.weight_port: str | None = None

    def discover_and_connect(self):
        """Portları tarar ve bulduğu sensörlere bağlanır."""
        # Geliştirici modunda port tarama atlanır, sahte portlar atanır.
        if settings.DEV_MODE:
            logger.info("DEV_MODE: Skipping real port discovery.")
            self.height_port = "DUMMY_H"
            self.weight_port = "DUMMY_W"
        else:
            # Gerçek port tarama (Bu fonksiyonu daha sonra dolduracağız)
            logger.info("Discovering sensor ports on Linux...")
            # Şimdilik sabit portlar atayalım, tarama mantığı sonra eklenecek.
            self.height_port = "/dev/ttyUSB0"
            self.weight_port = "/dev/ttyUSB1"

        self._connect_all()

    def _connect_all(self):
        """Tespit edilen portlara ve I2C cihazına bağlanır."""
        logger.info("Attempting to connect to all sensors...")

        # Mesafe (Yükseklik) Sensörü Bağlantısı
        if self.height_port and not self.is_height_connected:
            try:
                self.height_ser = serial.Serial(self.height_port, settings.SERIAL_BAUD_RATE, timeout=1.0)
                self.is_height_connected = True
                logger.info(f"Height sensor connected successfully on {self.height_port}.")
            except (serial.SerialException, FileNotFoundError) as e:
                logger.error(f"Failed to connect to height sensor on {self.height_port}: {e}")

        # Ağırlık Sensörü Bağlantısı
        if self.weight_port and not self.is_weight_connected:
            try:
                self.weight_ser = serial.Serial(self.weight_port, settings.SERIAL_BAUD_RATE, timeout=1.0)
                self.is_weight_connected = True
                logger.info(f"Weight sensor connected successfully on {self.weight_port}.")
            except (serial.SerialException, FileNotFoundError) as e:
                logger.error(f"Failed to connect to weight sensor on {self.weight_port}: {e}")

        # Sıcaklık/Nem (I2C) Sensörü Bağlantısı
        if not self.is_temp_hum_connected:
            try:
                self.i2c_bus = SMBus(settings.I2C_BUS)
                # DEV_MODE'da gerçek bir donanım testi yapmayız.
                if not settings.DEV_MODE:
                    self.i2c_bus.write_byte(settings.I2C_SHT3X_ADDRESS, 0x00)
                self.is_temp_hum_connected = True
                logger.info(f"Temp/Humidity sensor connected successfully on I2C bus {settings.I2C_BUS}.")
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error(f"Failed to connect to Temp/Humidity sensor (I2C): {e}")

    def disconnect_all(self):
        """Tüm aktif bağlantıları güvenli bir şekilde kapatır."""
        logger.info("Disconnecting all sensors...")
        if self.height_ser and self.height_ser.is_open:
            self.height_ser.close()
        if self.weight_ser and self.weight_ser.is_open:
            self.weight_ser.close()
        if self.i2c_bus:
            self.i2c_bus.close()
        logger.info("All sensor connections have been closed.")