import logging
from typing import List, Tuple

import pandas as pd
from app.config import settings
from app.models.schemas import RawSensorData, ProcessedReading
from app.sensors.parsers import (
    parse_height_from_raw,
    parse_weight_from_raw,
    parse_temp_hum_from_raw
)

logger = logging.getLogger(__name__)

class DataProcessor:
    # ... _validate_value, process_raw_data, _calculate... metodları aynı kalıyor ...
    def _validate_value(self, value: float | None, metric_name: str) -> Tuple[float | None, str]:
        if value is None:
            return None, "NO_DATA"
        min_val, max_val = settings.VALIDATION_RANGES.get(metric_name, (None, None))
        if min_val is not None and max_val is not None:
            if not (min_val <= value <= max_val):
                logger.warning(f"Validation failed for {metric_name}: value {value} is out of range ({min_val}, {max_val}).")
                return None, "OUT_OF_RANGE"
        return value, "OK"

    def process_raw_data(self, raw_data: RawSensorData) -> ProcessedReading:
        height = parse_height_from_raw(raw_data.height_raw)
        weight = parse_weight_from_raw(raw_data.weight_raw)
        temp, hum, source = None, None, "local"
        if raw_data.temp_hum_raw:
            temp, hum = parse_temp_hum_from_raw(raw_data.temp_hum_raw)
            source = "local"
        elif raw_data.temp_hum_api:
            temp, hum = raw_data.temp_hum_api
            source = "api"
            logger.info("Processing temperature/humidity data from API source.")
        valid_height, height_status = self._validate_value(height, "height_mm")
        valid_weight, weight_status = self._validate_value(weight, "weight_g")
        valid_temp, temp_status = self._validate_value(temp, "temperature_c")
        valid_hum, hum_status = self._validate_value(hum, "humidity_perc")
        snow_height = self._calculate_snow_height(valid_height)
        density = self._calculate_density(valid_weight, snow_height)
        return ProcessedReading(
            timestamp=raw_data.timestamp,
            height_mm=valid_height,
            weight_g=valid_weight,
            temperature_c=valid_temp,
            humidity_perc=valid_hum,
            snow_height_mm=snow_height,
            density_kg_m3=density,
            height_status=height_status,
            weight_status=weight_status,
            temperature_status=temp_status,
            humidity_status=hum_status,
            temp_hum_source=source
        )

    def _calculate_snow_height(self, height_mm: float | None) -> float | None:
        if height_mm is None: return None
        return max(0.0, settings.SENSOR_ZERO_DISTANCE_MM - height_mm)

    def _calculate_density(self, weight_g: float | None, snow_height_mm: float | None) -> float | None:
        if weight_g is None or snow_height_mm is None or snow_height_mm <= 0: return None
        try:
            mass_kg = weight_g / 1000.0
            snow_height_m = snow_height_mm / 1000.0
            volume_m3 = settings.MEASUREMENT_AREA_M2 * snow_height_m
            density = mass_kg / volume_m3
            return round(density, 2)
        except ZeroDivisionError:
            return None

    def analyze_burst_readings(self, readings: List[ProcessedReading]) -> ProcessedReading:
        """
        Bir okuma listesini (burst) alır, istatistiksel özetini (ortalama) hesaplar
        ve tek bir ProcessedReading nesnesi olarak döndürür.
        """
        if not readings:
            logger.warning("analyze_burst_readings called with an empty list.")
            return ProcessedReading()

        df = pd.DataFrame([r.model_dump() for r in readings])
        
        summary = ProcessedReading()
        summary.timestamp = pd.to_datetime(df['timestamp']).max().to_pydatetime()

        # Sayısal sütunların ortalamasını al
        numeric_cols = ["height_mm", "weight_g", "temperature_c", "humidity_perc", "snow_height_mm", "density_kg_m3"]
        for col in numeric_cols:
            if col in df and not df[col].isnull().all():
                # skipna=True, None değerleri görmezden gelerek ortalama alır.
                mean_value = df[col].mean(skipna=True)
                setattr(summary, col, mean_value)

        # Durum sütunlarının en sık görülenini (mod) al
        status_cols = ["height_status", "weight_status", "temperature_status", "humidity_status", "temp_hum_source"]
        for col in status_cols:
             if col in df and not df[col].empty:
                # 'mode()' bir Seri döndürebilir, her zaman ilkini al ([0])
                setattr(summary, col, df[col].mode()[0])

        return summary