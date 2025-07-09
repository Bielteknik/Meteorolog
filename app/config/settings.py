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

# Zamanlama Ayarları (dakika ve saniye cinsinden)
DATA_COLLECTION_INTERVAL_MINUTES: int = int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "5"))
DATA_COLLECTION_DURATION_SECONDS: int = int(os.getenv("DATA_COLLECTION_DURATION_SECONDS", "55"))
API_SEND_INTERVAL_MINUTES: int = int(os.getenv("API_SEND_INTERVAL_MINUTES", "60"))

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
EXTERNAL_API_ENDPOINT: str = os.getenv("EXTERNAL_API_ENDPOINT", "[...BURAYI DOLDUR...]")
OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "[...BURAYI DOLDUR...]")
OPENWEATHERMAP_CITY_ID: str = os.getenv("OPENWEATHERMAP_CITY_ID", "[...BURAYI DOLDUR...]")

# E-posta Ayarları
EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "False").lower() in ("true", "1", "t")
EMAIL_SMTP_SERVER: str = os.getenv("EMAIL_SMTP_SERVER", "[...BURAYI DOLDUR...]")
EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "[...BURAYI DOLDUR...]")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "[...BURAYI DOLDUR...]")
EMAIL_RECIPIENT: str = os.getenv("EMAIL_RECIPIENT", "[...BURAYI DOLDUR...]")