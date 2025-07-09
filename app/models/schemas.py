from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SensorReading(BaseModel):
    """Sensörlerden okunan ham (ama parse edilmiş) veriyi temsil eder."""
    timestamp: datetime = Field(default_factory=datetime.now)
    height_mm: Optional[float] = None
    weight_g: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_perc: Optional[float] = None

class ProcessedReading(SensorReading):
    """Hesaplanmış değerleri de içeren işlenmiş veri modeli."""
    snow_height_mm: Optional[float] = None
    density_kg_m3: Optional[float] = None