from abc import ABC, abstractmethod

class BaseSensor(ABC):
    """
    Tüm sensör plugin'leri için temel arayüz (şablon).
    Her yeni sensör tipi bu sınıfı miras almalı ve soyut metodları
    (abstractmethod) kendi mantığına göre doldurmalıdır.
    """
    def __init__(self, config: dict):
        """
        Her sensör, veritabanından gelen kendi konfigürasyon sözlüğü ile başlatılır.
        
        Args:
            config (dict): Veritabanından gelen ve sensörün ayarlarını içeren sözlük.
        """
        self.sensor_id = config.get("id")
        self.name = config.get("name")
        self.type = config.get("type")
        self.config = config
        self.port = None      # Atanacak olan seri port veya I2C adresi
        self.connection = None # Gerçek bağlantı nesnesi (örn: serial.Serial)

    @staticmethod
    @abstractmethod
    def check_fingerprint(data_sample: str, config: dict) -> bool:
        """
        Bir seri porttan okunan veri örneğinin (data_sample), bu sensör tipine
        ait olup olmadığını kontrol eder. Bu metod, sensör keşfi sırasında kullanılır.

        Args:
            data_sample (str): Seri porttan okunan birkaç satırlık veri.
            config (dict): Sensörün ayarları (örn: parmak izi regex'i için).
        
        Returns:
            bool: Veri bu sensöre aitse True, değilse False.
        """
        raise NotImplementedError

    @abstractmethod
    def connect(self, port: str) -> bool:
        """
        SensorManager tarafından port bulunduktan sonra, sensöre fiziksel
        bağlantıyı kurar.
        
        Args:
            port (str): Bağlanılacak olan seri port (örn: '/dev/ttyUSB0').

        Returns:
            bool: Bağlantı başarılı ise True, değilse False.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self):
        """
        Sensörden anlık veriyi okur.

        Returns:
            Veri (float, tuple, vb.) veya okuma başarısız olursa None.
        """
        raise NotImplementedError
        
    def disconnect(self):
        """Sensörle olan bağlantıyı güvenli bir şekilde kapatır."""
        if hasattr(self.connection, 'close') and self.connection.is_open:
            self.connection.close()
            print(f"🔌 {self.name} bağlantısı kapatıldı.")