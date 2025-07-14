# config.py
import yaml
from pydantic import BaseModel, Field
from typing import Optional

# YAML dosyasındaki her bir bölüm için Pydantic modelleri
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
    api_key: str
    openweathermap_key: str
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
    password: str
    recipient: str
    daily_limit: int

# Tüm yapılandırmayı içeren ana model
class Settings(BaseModel):
    station: StationConfig
    sensors: SensorsConfig
    scheduler: SchedulerConfig
    api: ApiConfig
    anomaly_rules: AnomalyRulesConfig
    email: EmailConfig

def load_config(path: str = "config.yaml") -> Settings:
    """
    YAML yapılandırma dosyasını okur, doğrular ve bir Settings nesnesi döndürür.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # YAML verisini Pydantic modeline yükle, doğrulama otomatik yapılır
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