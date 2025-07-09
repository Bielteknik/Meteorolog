from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RawSensorData(BaseModel):
    """
    Sensörlerden doğrudan okunan, henüz işlenmemiş ham veriyi temsil eder.
    Bu model, verinin ilk halini (genellikle byte dizisi veya ham metin) tutar.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    height_raw: Optional[bytes] = None
    weight_raw: Optional[bytes] = None
    temp_hum_raw: Optional[list] = None # I2C'den gelen byte listesi


class ProcessedReading(BaseModel):
    """
    Ham verinin işlenmiş, doğrulanmış ve ek hesaplamalar yapılmış halini temsil eder.
    Uygulama içinde ve veritabanına kaydederken bu modeli kullanacağız.
    """
    # Zaman damgası
    timestamp: datetime = Field(default_factory=datetime.now)

    # Temel Ölçümler (Doğrulanmış ve float'a çevrilmiş)
    height_mm: Optional[float] = None
    weight_g: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_perc: Optional[float] = None

    # Türetilmiş Ölçümler (Hesaplanan değerler)
    snow_height_mm: Optional[float] = None
    density_kg_m3: Optional[float] = None
    
    # Veri Kalitesi ve Durumu
    height_status: str = "NO_DATA"
    weight_status: str = "NO_DATA"
    temperature_status: str = "NO_DATA"
    humidity_status: str = "NO_DATA"

    class Config:
        # Bu modelin ekstra alanlara sahip olmasına izin verme (daha katı veri yapısı)
        extra = "forbid"