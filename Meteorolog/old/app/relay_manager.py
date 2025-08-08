import RPi.GPIO as GPIO
import time
from .config import settings

class RelayManager:
    """
    GPIO pinleri üzerinden 8'li röle kartını yönetir.
    Hangi sensörün hangi röle kanalına bağlı olduğu config dosyasından okunur.
    """
    def __init__(self):
        # Hangi sensörün hangi BCM pinine bağlı olduğu
        # --- DEĞİŞİKLİK: Bu yapılandırma artık config.py ve config.yaml'dan doğru şekilde okunacak ---
        self.RELAY_PINS = {
            'lidar': settings.relays.lidar_pin,
            'ultrasonic': settings.relays.ultrasonic_pin,
            'weight': settings.relays.weight_pin
            # Diğer sensörler için de eklenebilir
        }
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        for pin in self.RELAY_PINS.values():
            if pin is not None:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH) # Başlangıçta tüm röleler kapalı (HIGH = OFF)

        print("✅ Röle Yöneticisi başlatıldı.")

    def _set_relay(self, pin: int, state: bool):
        """Röleyi açar (True) veya kapatır (False)."""
        # Röle kartları genellikle LOW sinyali ile aktif olur (çeker).
        if state: # True = ON = LOW
            GPIO.output(pin, GPIO.LOW)
        else: # False = OFF = HIGH
            GPIO.output(pin, GPIO.HIGH)
            
    def power_on(self, sensor_name: str):
        """Belirtilen sensörün gücünü açar."""
        if pin := self.RELAY_PINS.get(sensor_name):
            print(f"⚡ Röle: '{sensor_name}' sensörünün gücü AÇILIYOR (Pin {pin}).")
            self._set_relay(pin, True)

    def power_off(self, sensor_name: str):
        """Belirtilen sensörün gücünü kapatır."""
        if pin := self.RELAY_PINS.get(sensor_name):
            print(f"🔌 Röle: '{sensor_name}' sensörünün gücü KAPATILIYOR (Pin {pin}).")
            self._set_relay(pin, False)
            
    def cleanup(self):
        """Uygulama kapatılırken tüm röleleri kapatır ve GPIO'yu temizler."""
        print("🧹 GPIO temizleniyor...")
        for pin in self.RELAY_PINS.values():
            if pin is not None:
                self._set_relay(pin, False) # Her şeyi kapat
        GPIO.cleanup()

# Global bir örnek oluşturalım
try:
    relay_manager = RelayManager()
except (RuntimeError, ModuleNotFoundError):
    # RPi.GPIO sadece Raspberry Pi'de çalışır.
    # Geliştirme ortamında (PC) hata vermemesi için sahte bir sınıf oluşturalım.
    print("⚠️  RPi.GPIO bulunamadı. Sahte RelayManager kullanılıyor.")
    class MockRelayManager:
        def power_on(self, sensor_name: str): print(f"⚡ (MOCK) Röle: '{sensor_name}' gücü AÇILDI.")
        def power_off(self, sensor_name: str): print(f"🔌 (MOCK) Röle: '{sensor_name}' gücü KAPATILDI.")
        def cleanup(self): print("🧹 (MOCK) GPIO temizlendi.")
    relay_manager = MockRelayManager()