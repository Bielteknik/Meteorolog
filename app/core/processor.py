# app/core/processor.py - GÜNCELLENMİŞ NİHAİ VERSİYON

import pandas as pd
from typing import List
from datetime import datetime

from app.config import settings
from app.models.schemas import SensorReading, ProcessedReading

class DataProcessor:
    """
    Sensör verilerini işler, ek hesaplamalar yapar ve toplu analiz gerçekleştirir.
    """
    def process(self, reading: SensorReading) -> ProcessedReading:
        """
        Bir SensorReading nesnesini alır ve hesaplanmış değerlerle birlikte
        bir ProcessedReading nesnesi döndürür.
        """
        snow_height = self._calculate_snow_height(reading.height_mm)
        density = self._calculate_density(
            weight_g=reading.weight_g,
            snow_height_mm=snow_height
        )

        # ProcessedReading nesnesini oluştururken,
        # temel okuma verilerini ve yeni hesaplanan verileri birleştiriyoruz.
        return ProcessedReading(
            **reading.model_dump(),  # SensorReading'den gelen tüm verileri kopyala
            snow_height_mm=snow_height,
            density_kg_m3=density
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
            # Döngüde hiç veri toplanamadıysa, None değerleri içeren boş bir model döndür
            return ProcessedReading(timestamp=datetime.now())

        # Verileri kolay analiz için bir pandas DataFrame'e dönüştür
        df = pd.DataFrame([r.model_dump() for r in readings])

        # Ortalama değerleri hesapla, olmayan (NaN) değerleri atla
        summary = {
            "timestamp": datetime.now(), # Özetin oluşturulduğu anın zaman damgası
            "height_mm": df['height_mm'].mean(skipna=True),
            "weight_g": df['weight_g'].mean(skipna=True),
            "temperature_c": df['temperature_c'].mean(skipna=True),
            "humidity_perc": df['humidity_perc'].mean(skipna=True),
            "snow_height_mm": df['snow_height_mm'].mean(skipna=True),
            "density_kg_m3": df['density_kg_m3'].mean(skipna=True),
        }
        
        # Olası NaN (hesaplanamayan) değerleri Python'un None tipine çevir
        for key, value in summary.items():
            if pd.isna(value):
                summary[key] = None

        return ProcessedReading(**summary)