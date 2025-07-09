# app/config/settings.py - GÜNCELLENMİŞ NİHAİ VERSİYON

import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kök dizinini belirle
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Genel Ayarlar
LOG_FILE_PREFIX: str = "sensor_data_log"
CSV_FOLDER: str = str(BASE_DIR / "data" / "csv_exports")
DATABASE_FILE_PATH: str = str(BASE_DIR / "data" / "weather_station.sqlite")

# --- YENİ ZAMANLAMA AYARLARI ---
# Ana döngünün ne sıklıkla çalışacağını belirler (dakika cinsinden).
DATA_COLLECTION_INTERVAL_MINUTES: int = int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "30"))

# Her döngüde, veri toplamanın ne kadar süreceğini belirler (dakika cinsinden).
DATA_BURST_DURATION_MINUTES: int = int(os.getenv("DATA_BURST_DURATION_MINUTES", "3"))

# Veri toplama süresi boyunca, ne sıklıkla örnek alınacağını belirler (saniye cinsinden).
DATA_BURST_SAMPLE_INTERVAL_SECONDS: int = int(os.getenv("DATA_BURST_SAMPLE_INTERVAL_SECONDS", "2"))


# Sensör Ayarları
SENSOR_ZERO_DISTANCE_MM: float = float(os.getenv("SENSOR_ZERO_DISTANCE_MM", "3700.0"))
MEASUREMENT_AREA_M2: float = float(os.getenv("MEASUREMENT_AREA_M2", "1.0"))
I2C_BUS: int = 1
I2C_SHT3X_ADDRESS: int = 0x44
SERIAL_BAUD_RATE: int = 9600
SERIAL_PROBE_TIMEOUT_S: float = 0.5
SERIAL_READ_TIMEOUT_S: float = 1.0

# Veri Doğrulama Aralıkları (Validation Ranges)
VALIDATION_RANGES = {
    "height_mm": (0, 10000),
    "weight_g": (0, 1000000),
    "temperature_c": (-40, 85),
    "humidity_perc": (0, 100),
}

# API Ayarları
# API_SEND_INTERVAL_MINUTES, EXTERNAL_API_ENDPOINT, OPENWEATHERMAP_API_KEY, OPENWEATHERMAP_CITY_ID
# Bu ayarlar şu anki mantıkta kullanılmıyor ama gelecekteki geliştirmeler için burada kalabilir.

# E-posta Ayarları
EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "False").lower() in ("true", "1", "t")
EMAIL_SMTP_SERVER: str = os.getenv("EMAIL_SMTP_SERVER", "smtp.example.com")
EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "user@example.com")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "password")
EMAIL_RECIPIENT: str = os.getenv("EMAIL_RECIPIENT", "recipient@example.com")