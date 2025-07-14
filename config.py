# config.py
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# ==============================================================================
# Model Tanımları
# ==============================================================================

# --- .env dosyasından okunacak Sırlar için Modeller ---
# BaseSettings, .env dosyasını otomatik olarak okur.
class ApiSecrets(BaseSettings):
    api_key: str = Field(..., alias='API_KEY')
    openweathermap_key: str = Field(..., alias='OPENWEATHERMAP_KEY')

class EmailSecrets(BaseSettings):
    password: str = Field(..., alias='EMAIL_PASSWORD')

# --- config.yaml dosyasından okunacak Ayarlar için Modeller ---
# BaseModel, sadece veri doğrulaması yapar.
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
# "&" operatörü ile iki modeli birleştiriyoruz.
class FinalApiConfig(ApiConfig, ApiSecrets):
    pass

class FinalEmailConfig(EmailConfig, EmailSecrets):
    pass

class Settings(BaseModel):
    station: StationConfig
    sensors: SensorsConfig
    scheduler: SchedulerConfig
    api: FinalApiConfig
    anomaly_rules: AnomalyRulesConfig
    email: FinalEmailConfig


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

        # 2. .env dosyasından sırları otomatik olarak yükle
        # Pydantic-settings bunu arka planda yapar.
        # Biz sadece Final... modellerini çağırırız.
        final_api_config = FinalApiConfig(**config_data.get('api', {}))
        final_email_config = FinalEmailConfig(**config_data.get('email', {}))

        # 3. Yüklenmiş verileri ana yapıya yerleştir
        config_data['api'] = final_api_config
        config_data['email'] = final_email_config

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
# Bu, diğer modüllerin "from config import settings" yapmasını sağlar.
settings = load_config()