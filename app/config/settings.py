import os
import platform
from pathlib import Path
from dotenv import load_dotenv

# --- Proje Kök Dizini ve .env Dosyasını Yükleme ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


# --- Geliştirici Modu (Platform Bağımsız Çalışma İçin) ---
DEV_MODE: bool = platform.system() == "Windows"


# --- Veritabanı ve Depolama Yolları ---
DATA_DIR = BASE_DIR / "data"
CSV_FOLDER: str = str(DATA_DIR / "csv_exports")
DATABASE_FILE_PATH: str = str(DATA_DIR / "weather_station.sqlite")


# --- Zamanlama Ayarları ---
DATA_COLLECTION_INTERVAL_MINUTES: int = int(os.getenv("DATA_COLLECTION_INTERVAL_MINUTES", "30"))
DATA_BURST_DURATION_MINUTES: int = int(os.getenv("DATA_BURST_DURATION_MINUTES", "3"))
DATA_BURST_SAMPLE_INTERVAL_SECONDS: int = int(os.getenv("DATA_BURST_SAMPLE_INTERVAL_SECONDS", "2"))


# --- Sensör Ayarları ---
# Not: Seri port isimleri (SENSOR_HEIGHT_PORT vb.) kaldırıldı.
# Sistem artık portları otomatik olarak "koklayarak" buluyor.
SENSOR_ZERO_DISTANCE_MM: float = float(os.getenv("SENSOR_ZERO_DISTANCE_MM", "3700.0"))
MEASUREMENT_AREA_M2: float = float(os.getenv("MEASUREMENT_AREA_M2", "1.0"))
I2C_BUS: int = 1
I2C_SHT3X_ADDRESS: int = 0x44
SERIAL_BAUD_RATE: int = 9600


# --- Veri Doğrulama Aralıkları ---
VALIDATION_RANGES = {
    "height_mm": (0, 10000),
    "weight_g": (0, 1000000),
    "temperature_c": (-40, 85),
    "humidity_perc": (0, 100),
}


# --- E-posta Ayarları ---
EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "False").lower() in ("true", "1", "t")
EMAIL_SMTP_SERVER: str = os.getenv("METEO_EMAIL_SMTP_SERVER", "")
EMAIL_SMTP_PORT: int = int(os.getenv("METEO_EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT: str = os.getenv("EMAIL_RECIPIENT", "")