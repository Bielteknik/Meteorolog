from pydantic import BaseModel, Field
from typing import Optional, Tuple
from datetime import datetime

class RawSensorData(BaseModel):
    """
    Sensörlerden veya API'lerden okunan, henüz işlenmemiş ham veriyi temsil eder.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    height_raw: Optional[bytes] = None
    weight_raw: Optional[bytes] = None
    temp_hum_raw: Optional[list] = None  # I2C'den gelen byte listesi
    temp_hum_api: Optional[Tuple[float, float]] = None # (sıcaklık, nem)


class ProcessedReading(BaseModel):
    """
    Ham verinin işlenmiş, doğrulanmış ve ek hesaplamalar yapılmış halini temsil eder.
    """
    timestamp: datetime = Field(default_factory=datetime.now)

    # Temel Ölçümler
    height_mm: Optional[float] = None
    weight_g: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_perc: Optional[float] = None

    # Türetilmiş Ölçümler
    snow_height_mm: Optional[float] = None
    density_kg_m3: Optional[float] = None
    
    # Veri Kalitesi ve Durumu
    # Mümkün durumlar: "OK", "NO_DATA", "OUT_OF_RANGE", "ANOMALY_SPIKE", "ANOMALY_STALL"
    height_status: str = "NO_DATA"
    weight_status: str = "NO_DATA"
    temperature_status: str = "NO_DATA"
    humidity_status: str = "NO_DATA"

    # Veri Kaynağı
    temp_hum_source: str = "local" # 'local' veya 'api'

    class Config:
        extra = "forbid"