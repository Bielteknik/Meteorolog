import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional

# ==============================================================================
# Model Tanımları
# ==============================================================================

# --- YENİ EKLENEN MODEL: Röle pinleri için ---
class RelaysConfig(BaseModel):
    # Pin numaraları BCM moduna göre olmalıdır.
    # Kullanılmayan sensörler için null veya None olarak bırakılabilir.
    lidar_pin: Optional[int] = None
    ultrasonic_pin: Optional[int] = None
    weight_pin: Optional[int] = None

# --- .env dosyasından okunacak Sırlar için ---
class Secrets(BaseSettings):
    openweathermap_key: str = Field(..., alias='OPENWEATHERMAP_KEY')
    password: str = Field(..., alias='EMAIL_PASSWORD')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# --- config.yaml dosyasından okunacak Ayarlar için Modeller ---
class StationConfig(BaseModel):
    id: str
    measurement_area_m2: float

class SensorsConfig(BaseModel):
    height_sensor_zero_mm: int

class SchedulerConfig(BaseModel):
    collection_interval_minutes: int
    collection_duration_minutes: int
    api_summary_hour: str
    maintenance_interval_minutes: int

class ApiConfig(BaseModel):
    base_url: str
    city_id: int
    latitude: float
    longitude: float

class AnomalyRulesConfig(BaseModel):
    critical_snow_increase_cm_per_hour: float
    critical_temp_pattern_enabled: bool
    frozen_sensor_threshold_cycles: int
    max_temp_change_per_cycle: float
    max_snow_height_change_per_cycle_cm: float

class EmailConfig(BaseModel):
    enabled: bool
    smtp_server: str
    smtp_port: int
    sender: str
    recipient: str
    daily_limit: int

# --- Tüm Yapılandırmayı Birleştiren Ana Model ---
class Settings(BaseModel):
    # --- DEĞİŞİKLİK: Yeni relays modeli eklendi ---
    relays: RelaysConfig
    station: StationConfig
    sensors: SensorsConfig
    scheduler: SchedulerConfig
    api: ApiConfig
    anomaly_rules: AnomalyRulesConfig
    email: EmailConfig
    secrets: Secrets

# ==============================================================================
# Yükleyici Fonksiyon
# ==============================================================================

def load_config(path: str = "config.yaml") -> Settings:
    """
    YAML ve .env dosyalarındaki yapılandırmaları okur, birleştirir,
    doğrular ve bir Settings nesnesi döndürür.
    """
    try:
        # 1. YAML dosyasını oku
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # 2. .env dosyasından sırları yükle
        secrets_data = Secrets()
        
        # 3. Sırları ana yapılandırma verisine ekle
        config_data['secrets'] = secrets_data

        # 4. Birleştirilmiş veriyi ana Pydantic modeline yükle
        settings = Settings(**config_data)
        return settings
    except FileNotFoundError:
        print(f"HATA: Yapılandırma dosyası bulunamadı: {path}")
        exit(1)
    except Exception as e:
        print(f"HATA: Yapılandırma dosyasını okurken bir hata oluştu: {e}")
        exit(1)

# Ayarları global olarak erişilebilir yapmak için bir örnek oluştur
settings = load_config()