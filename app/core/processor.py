import pandas as pd
from typing import List, Tuple
from datetime import datetime

from app.config import settings
from app.models.schemas import SensorReading, ProcessedReading

class DataProcessor:
    """
    Sensör verilerini işler, ek hesaplamalar yapar ve toplu analiz gerçekleştirir.
    """

    def _validate_value(self, value: float | None, metric_name: str) -> Tuple[float | None, str]:
        """
        Bir değeri alır, doğrulama aralığını kontrol eder ve değeri ile durumunu döndürür.
        YENİ EKLENEN YARDIMCI METOT.
        """
        if value is None:
            return None, "NO_DATA"

        min_val, max_val = settings.VALIDATION_RANGES.get(metric_name, (None, None))
        
        if min_val is not None and max_val is not None:
            if not (min_val <= value <= max_val):
                # Değer aralık dışındaysa, değeri geçersiz say (None) ve durumu bildir.
                return None, "OUT_OF_RANGE"
        
        return value, "OK"

    def process(self, reading: SensorReading) -> ProcessedReading:
        """
        Bir SensorReading nesnesini alır, doğrular, hesaplanmış değerlerle birlikte
        bir ProcessedReading nesnesi döndürür. BU METOT GÜNCELLENDİ.
        """
        # 1. Ham okumaları doğrula
        valid_height, height_status = self._validate_value(reading.height_mm, "height_mm")
        valid_weight, weight_status = self._validate_value(reading.weight_g, "weight_g")
        valid_temp, temp_status = self._validate_value(reading.temperature_c, "temperature_c")
        valid_hum, hum_status = self._validate_value(reading.humidity_perc, "humidity_perc")

        # 2. Doğrulanmış değerler üzerinden hesaplamaları yap
        snow_height = self._calculate_snow_height(valid_height)
        density = self._calculate_density(
            weight_g=valid_weight,
            snow_height_mm=snow_height
        )

        # 3. Tüm verileri ve durumları içeren ProcessedReading nesnesini oluştur
        return ProcessedReading(
            timestamp=reading.timestamp,
            height_mm=valid_height,
            weight_g=valid_weight,
            temperature_c=valid_temp,
            humidity_perc=valid_hum,
            snow_height_mm=snow_height,
            density_kg_m3=density,
            height_status=height_status,
            weight_status=weight_status,
            temperature_status=temp_status,
            humidity_status=hum_status
        )

    def _calculate_snow_height(self, height_mm: float | None) -> float | None:
        """Mesafe okumasından kar yüksekliğini hesaplar."""
        if height_mm is None:
            return None
        return max(0.0, settings.SENSOR_ZERO_DISTANCE_MM - height_mm)

    def _calculate_density(self, weight_g: float | None, snow_height_mm: float | None) -> float | None:
        """Ağırlık ve kar yüksekliğinden yoğunluğu (kg/m³) hesaplar."""
        if weight_g is None or snow_height_mm is None or snow_height_mm <= 0:
            return None

        try:
            mass_kg = weight_g / 1000.0
            snow_height_m = snow_height_mm / 1000.0
            volume_m3 = settings.MEASUREMENT_AREA_M2 * snow_height_m
            
            density = mass_kg / volume_m3
            return round(density, 2)
        except ZeroDivisionError:
            return None

    def analyze_readings(self, readings: List[ProcessedReading]) -> ProcessedReading:
        """
        Bir okuma listesini alır, istatistiksel özetini (ortalama) hesaplar
        ve tek bir ProcessedReading nesnesi olarak döndürür.
        """
        if not readings:
            return ProcessedReading(timestamp=datetime.now())

        df = pd.DataFrame([r.model_dump() for r in readings])

        # Ortalama değerleri hesapla, olmayan (NaN) değerleri atla
        summary = {
            "timestamp": datetime.now(),
            "height_mm": df['height_mm'].mean(skipna=True),
            "weight_g": df['weight_g'].mean(skipna=True),
            "temperature_c": df['temperature_c'].mean(skipna=True),
            "humidity_perc": df['humidity_perc'].mean(skipna=True),
            "snow_height_mm": df['snow_height_mm'].mean(skipna=True),
            "density_kg_m3": df['density_kg_m3'].mean(skipna=True),
            # Durumlar için en sık görülen durumu seçebiliriz (opsiyonel)
            "height_status": df['height_status'].mode()[0] if not df['height_status'].empty else "NO_DATA",
            "weight_status": df['weight_status'].mode()[0] if not df['weight_status'].empty else "NO_DATA",
            "temperature_status": df['temperature_status'].mode()[0] if not df['temperature_status'].empty else "NO_DATA",
            "humidity_status": df['humidity_status'].mode()[0] if not df['humidity_status'].empty else "NO_DATA",
        }
        
        for key, value in summary.items():
            if pd.isna(value):
                summary[key] = None

        return ProcessedReading(**summary)